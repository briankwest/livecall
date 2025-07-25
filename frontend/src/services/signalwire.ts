import { api } from './api';
import type { 
  SignalWireClient, 
  FabricRoomSession, 
  IncomingCallNotification,
  OnlineParams,
  DialParams
} from '../types/signalwire';

// SignalWire is loaded globally from CDN

export interface WebPhoneConfig {
  token: string;
}

export interface CallState {
  id: string;
  direction: 'inbound' | 'outbound';
  state: 'new' | 'requesting' | 'trying' | 'active' | 'hangup' | 'destroy';
  phoneNumber: string;
  startTime?: Date;
  endTime?: Date;
  muted: boolean;
  onHold: boolean;
}

class SignalWireService {
  private client: SignalWireClient | null = null;
  private currentCall: FabricRoomSession | null = null;
  private config: WebPhoneConfig | null = null;
  private eventHandlers: Map<string, Function[]> = new Map();
  private isDialing: boolean = false;
  private muted: boolean = false;
  private onHold: boolean = false;

  async initialize(): Promise<void> {
    try {
      // Clear any existing SignalWire tokens from localStorage and sessionStorage
      ['localStorage', 'sessionStorage'].forEach(storageType => {
        const storage = window[storageType as 'localStorage' | 'sessionStorage'];
        const keysToRemove: string[] = [];
        
        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i);
          if (key && (key.includes('-SAT') || key.includes('signalwire') || key.includes('fabric'))) {
            keysToRemove.push(key);
          }
        }
        
        keysToRemove.forEach(key => {
          console.log(`Removing cached token from ${storageType}:`, key);
          storage.removeItem(key);
        });
      });
      
      // Get SignalWire token from backend
      const response = await api.post('/api/auth/signalwire-token');
      const { token } = response.data;
      
      // Get the root element for video display
      const rootElement = document.getElementById('signalwire-container');
      
      // Initialize the SignalWire client with the token
      const options: { token: string; rootElement?: HTMLElement } = {
        token: token
      };
      
      // Only add rootElement if it exists
      if (rootElement) {
        options.rootElement = rootElement;
      }
      
      // Try different initialization methods
      let client = null;
      
      if (SignalWire.Fabric && SignalWire.Fabric.Client && typeof SignalWire.Fabric.Client === 'function') {
        console.log('Using new SignalWire.Fabric.Client()');
        client = new SignalWire.Fabric.Client(options);
      } else if (typeof SignalWire.SignalWire === 'function') {
        console.log('Using SignalWire.SignalWire()');
        client = await SignalWire.SignalWire(options);
      } else if (typeof SignalWire === 'function') {
        console.log('Using SignalWire directly');
        client = await SignalWire(options);
      } else {
        throw new Error('No suitable SignalWire initialization method found');
      }
      
      this.client = client;
      console.log('Client created:', this.client);

      // Set client to online to receive calls
      await this.client.online({
        incomingCallHandlers: { all: this.handleIncomingCall.bind(this) }
      });
      
      console.log('Connected to SignalWire');
    } catch (error) {
      console.error('Error connecting to SignalWire:', error);
      throw error;
    }
  }

  private async handleIncomingCall(notification: IncomingCallNotification): Promise<void> {
    console.log('Incoming call notification:', notification);
    
    // Store the invite for later use (accept/reject)
    this.currentCall = notification.invite;
    
    // Extract caller info from invite
    const callerId = this.extractCallerId(notification.invite);
    
    // Don't set up event handlers on invite - only on accepted call
    // The invite object doesn't have .on() method
    
    this.emit('call.received', {
      id: notification.invite.id || Date.now().toString(),
      direction: 'inbound',
      state: 'new',
      phoneNumber: callerId,
      muted: false,
      onHold: false,
    });
  }

  private extractCallerId(call: any): string {
    // Try various properties where caller ID might be stored
    return call?.details?.caller_id_number || 
           call?.remoteCallerNumber || 
           call?.callerNumber || 
           'Unknown';
  }

  async makeCall(phoneNumber: string): Promise<string> {
    console.log('=== makeCall() CALLED ===');
    console.log('Phone number:', phoneNumber);
    
    if (!this.client) {
      console.error('SignalWire client not initialized!');
      throw new Error('SignalWire client not initialized');
    }

    // Prevent multiple simultaneous dial attempts
    if (this.isDialing) {
      console.log('Already dialing, ignoring duplicate request');
      throw new Error('Call already in progress');
    }

    // Check if we already have an active call
    if (this.currentCall) {
      console.log('Active call exists, cannot make new call');
      throw new Error('Active call already exists');
    }

    this.isDialing = true;
    this.muted = false;
    this.onHold = false;

    try {
      const rootElement = document.getElementById('signalwire-container');
      
      const dialParams: DialParams = {
        to: '/public/call-pstn',
        audio: true,
        video: false,
        userVariables: {
          destination_number: phoneNumber,
          from_number: '',
          direction: 'outbound'
        },
        ...(rootElement && { rootElement })
      };
      
      console.log('Dial params:', dialParams);
      
      // Create a call using SDK dial method
      const call = await this.client.dial(dialParams);
      console.log('client.dial() returned call:', call);
      
      this.currentCall = call;
      this.setupCallEventHandlers(call);
      
      // Start the call
      console.log('Starting call...');
      await call.start();
      console.log('Call started successfully');
      
      this.isDialing = false;
      this.emit('call.started', {
        id: call.id,
        direction: 'outbound',
        state: 'trying',
        phoneNumber: phoneNumber,
        muted: false,
        onHold: false,
      });

      return call.id;
    } catch (error) {
      console.error('Failed to make call:', error);
      // Reset state on error
      this.isDialing = false;
      this.currentCall = null;
      throw error;
    }
  }

  private setupCallEventHandlers(call: FabricRoomSession): void {
    // Handle call destruction - this is the CRITICAL event when call ends
    call.on('destroy', () => {
      console.log('===== CALL DESTROY EVENT - RESETTING IMMEDIATELY =====');
      // Clear the call reference immediately
      const callId = call.id;
      this.currentCall = null;
      this.isDialing = false;
      this.muted = false;
      this.onHold = false;
      
      // Emit call.ended immediately to reset UI
      this.emit('call.ended', { id: callId });
      console.log('===== EMITTED call.ended - WebPhone should be idle now =====');
    });
    
    // Handle state changes
    call.on('state', (state: string) => {
      console.log('Call state changed to:', state);
      if (state === 'destroy') {
        // Double-check destroy state
        console.log('State is destroy - call should be ending');
      }
      this.emit('call.state', { 
        id: call.id, 
        state: state 
      });
    });
    
    // Handle media events
    call.on('media.connected', () => {
      console.log('Media connected');
      this.emit('call.state', { 
        id: call.id, 
        state: 'active' 
      });
    });
    
    call.on('media.disconnected', () => {
      console.log('Media disconnected');
    });
    
    // Map room.subscribed to our active state
    call.on('room.subscribed', () => {
      console.log('Room subscribed - call is active');
      this.emit('call.state', { 
        id: call.id, 
        state: 'active' 
      });
    });
    
    // Also listen for other call end events
    call.on('hangup', () => {
      console.log('Call hangup event');
      this.emit('call.state', { 
        id: call.id, 
        state: 'hangup' 
      });
    });
    
    // Listen for any errors
    call.on('error', (error: any) => {
      console.error('Call error:', error);
      // On error, also end the call
      this.handleCallEnded(call.id);
    });
  }

  private handleCallEnded(callId: string): void {
    console.log('handleCallEnded called for call:', callId);
    this.currentCall = null;
    this.isDialing = false;
    this.muted = false;
    this.onHold = false;
    this.emit('call.ended', { id: callId });
    console.log('Emitted call.ended event');
  }

  async answerCall(): Promise<void> {
    if (!this.currentCall) {
      throw new Error('No incoming call to answer');
    }

    try {
      const rootElement = document.getElementById('signalwire-container');
      const options = rootElement ? { rootElement } : {};
      
      // Accept returns the active call session
      const call = await this.currentCall.accept!(options);
      this.currentCall = call;
      this.setupCallEventHandlers(call);
      
      this.emit('call.answered', {
        id: call.id,
        direction: 'inbound',
        state: 'active',
      });
    } catch (error) {
      console.error('Failed to answer call:', error);
      throw error;
    }
  }

  async rejectCall(): Promise<void> {
    if (!this.currentCall) {
      throw new Error('No incoming call to reject');
    }

    try {
      await this.currentCall.reject!();
      this.currentCall = null;
    } catch (error) {
      console.error('Failed to reject call:', error);
      throw error;
    }
  }

  async hangupCall(): Promise<void> {
    if (!this.currentCall) {
      throw new Error('No active call to hang up');
    }

    // Check if call is already destroyed (like client.js does)
    if (this.currentCall.state === 'destroy') {
      console.log('Call already destroyed, skipping hangup');
      return;
    }

    const callId = this.currentCall.id;
    
    try {
      // Use the proper SDK method
      if (typeof this.currentCall.leave === 'function') {
        console.log('Calling leave on call');
        await this.currentCall.leave();
      } else if (typeof this.currentCall.hangup === 'function') {
        console.log('Calling hangup on call');
        await this.currentCall.hangup();
      } else {
        console.error('No leave or hangup method found on call object');
        throw new Error('Cannot end call - no appropriate method found');
      }
      
      // The destroy event handler will also handle cleanup
      // But emit ended event immediately for UI responsiveness (like client.js resetUI)
      console.log('Hangup initiated, emitting call.ended immediately');
      this.handleCallEnded(callId);
    } catch (error) {
      console.error('Failed to hang up call:', error);
      // Still handle the call ended in case of error
      this.handleCallEnded(callId);
      throw error;
    }
  }

  async toggleMute(): Promise<boolean> {
    if (!this.currentCall) {
      throw new Error('No active call');
    }

    try {
      if (this.muted) {
        await this.currentCall.audioUnmute();
        this.muted = false;
      } else {
        await this.currentCall.audioMute();
        this.muted = true;
      }
      
      this.emit('call.muted', { 
        id: this.currentCall.id, 
        muted: this.muted 
      });
      
      return this.muted;
    } catch (error) {
      console.error('Failed to toggle mute:', error);
      throw error;
    }
  }

  async toggleHold(): Promise<boolean> {
    if (!this.currentCall) {
      throw new Error('No active call');
    }

    try {
      if (this.onHold) {
        await this.currentCall.unhold();
        this.onHold = false;
      } else {
        await this.currentCall.hold();
        this.onHold = true;
      }
      
      this.emit('call.hold', { 
        id: this.currentCall.id, 
        onHold: this.onHold 
      });
      
      return this.onHold;
    } catch (error) {
      console.error('Failed to toggle hold:', error);
      throw error;
    }
  }

  async sendDTMF(digit: string): Promise<void> {
    if (!this.currentCall) {
      throw new Error('No active call');
    }

    try {
      // Use the correct SDK method name
      await this.currentCall.sendDigits(digit);
    } catch (error) {
      console.error('Failed to send DTMF:', error);
      throw error;
    }
  }

  on(event: string, handler: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  off(event: string, handler: Function): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }
  
  getCurrentCall(): FabricRoomSession | null {
    return this.currentCall;
  }

  async disconnect(): Promise<void> {
    if (this.currentCall) {
      try {
        if (typeof this.currentCall.leave === 'function') {
          await this.currentCall.leave();
        } else if (typeof this.currentCall.hangup === 'function') {
          await this.currentCall.hangup();
        }
      } catch (error) {
        console.error('Error ending call during disconnect:', error);
      }
    }
    
    if (this.client) {
      try {
        await this.client.offline();
        await this.client.disconnect();
      } catch (error) {
        console.error('Error disconnecting client:', error);
      }
    }
    
    this.client = null;
    this.currentCall = null;
    this.eventHandlers.clear();
  }

  get hasActiveCall(): boolean {
    return !!this.currentCall;
  }

  get isInitialized(): boolean {
    return !!this.client;
  }
}

export const signalWireService = new SignalWireService();