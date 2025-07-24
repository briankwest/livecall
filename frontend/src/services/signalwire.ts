import { api } from './api';

// SignalWire is loaded globally from CDN
declare global {
  interface Window {
    SignalWire: any;
  }
  const SignalWire: any;
}

export interface WebPhoneConfig {
  token: string;
  project_id: string;
  space_url: string;
  from_number?: string;
}

export interface CallState {
  id: string;
  direction: 'inbound' | 'outbound';
  state: 'new' | 'trying' | 'ringing' | 'answered' | 'ending' | 'ended';
  phoneNumber: string;
  startTime?: Date;
  endTime?: Date;
  muted: boolean;
  onHold: boolean;
}

class SignalWireService {
  private client: any = null;
  private currentCall: any = null;
  private config: WebPhoneConfig | null = null;
  private eventHandlers: Map<string, Function[]> = new Map();

  async initialize(): Promise<void> {
    try {
      // Check if SignalWire is loaded
      if (typeof SignalWire === 'undefined') {
        throw new Error('SignalWire SDK not loaded');
      }
      console.log('SignalWire SDK available:', typeof SignalWire);

      // Get SignalWire token from backend
      const response = await api.post('/api/auth/signalwire-token');
      this.config = response.data;
      console.log('SignalWire config received:', this.config);

      // Create SignalWire client based on v3 SDK
      if (!this.config || !this.config.token) {
        throw new Error('Config or token not loaded');
      }
      
      console.log('Initializing SignalWire with token:', this.config.token.substring(0, 50) + '...');
      console.log('Token type:', typeof this.config.token);
      console.log('Token length:', this.config.token.length);
      
      // Initialize SignalWire client using the correct method
      // @ts-ignore - SignalWire is loaded from CDN
      const clientOptions = {
        token: this.config.token
      };
      
      const rootElement = document.getElementById('signalwire-container');
      if (rootElement) {
        // @ts-ignore
        clientOptions.rootElement = rootElement;
      }
      
      console.log('Creating SignalWire client with options:', clientOptions);
      
      // Add timeout to detect if it's hanging
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('SignalWire initialization timeout after 10 seconds')), 10000);
      });
      
      try {
        this.client = await Promise.race([
          SignalWire.SignalWire(clientOptions),
          timeoutPromise
        ]);
        console.log('SignalWire client created successfully:', this.client);
      } catch (timeoutError) {
        console.error('SignalWire initialization failed or timed out:', timeoutError);
        throw timeoutError;
      }

      // Set client online to receive calls with incoming call handler
      await this.client.online({
        incomingCallHandlers: { 
          all: this.handleIncomingCall.bind(this)
        }
      });
      
      console.log('SignalWire online successful');
    } catch (error: any) {
      console.error('Failed to initialize SignalWire client:', error);
      console.error('Error type:', error?.name || 'Unknown');
      console.error('Error message:', error?.message || 'No message');
      console.error('Error stack:', error?.stack || 'No stack');
      
      // Check for specific error types
      if (error?.message?.includes('token')) {
        console.error('Token-related error detected');
      }
      if (error?.message?.includes('auth')) {
        console.error('Authentication error detected');
      }
      
      // Log the full error object
      try {
        console.error('Full error object:', JSON.stringify(error, Object.getOwnPropertyNames(error), 2));
      } catch (e) {
        console.error('Could not stringify error object');
      }
      
      throw error;
    }
  }

  private async handleIncomingCall(notification: any): Promise<void> {
    console.log('Incoming call notification:', notification);
    
    // Store the invite for later use (accept/reject)
    this.currentCall = notification.invite;
    
    const callerId = notification.invite?.details?.caller_id_number || 'Unknown';
    
    this.emit('call.received', {
      id: notification.invite.id,
      direction: 'inbound',
      state: 'ringing',
      phoneNumber: callerId,
      muted: false,
      onHold: false,
    });
  }

  async makeCall(phoneNumber: string): Promise<string> {
    if (!this.client) {
      throw new Error('SignalWire client not initialized');
    }

    try {
      // Create call options
      const rootElement = document.getElementById('signalwire-container');
      const options: any = {
        to: '/public/call-pstn',  // SignalWire Call Fabric endpoint
        audio: true,
        video: false,
        userVariables: {
          destination_number: phoneNumber,
          from_number: this.config?.from_number || ''
        }
      };
      
      if (rootElement) {
        options.rootElement = rootElement;
      }
      
      // Create a call
      const call = await this.client.dial(options);
      
      // Set up event handler for call end
      call.on('destroy', () => {
        console.log('Call ended');
        this.currentCall = null;
        this.emit('call.ended', { id: call.id });
      });
      
      // Start the call
      await call.start();
      this.currentCall = call;

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
      throw error;
    }
  }

  async answerCall(): Promise<void> {
    if (!this.currentCall) {
      throw new Error('No incoming call to answer');
    }

    try {
      // Accept the call with rootElement
      const rootElement = document.getElementById('signalwire-container');
      const options: any = {};
      if (rootElement) {
        options.rootElement = rootElement;
      }
      
      const call = await this.currentCall.accept(options);
      this.currentCall = call;
      
      // Set up event handler for call end
      call.on('destroy', () => {
        console.log('Call ended');
        this.currentCall = null;
        this.emit('call.ended', { id: call.id });
      });
      
      this.emit('call.answered', {
        id: call.id,
        direction: 'inbound',
        state: 'answered',
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
      await this.currentCall.reject();
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

    try {
      await this.currentCall.hangup();
      this.currentCall = null;
    } catch (error) {
      console.error('Failed to hang up call:', error);
      throw error;
    }
  }

  async toggleMute(): Promise<boolean> {
    if (!this.currentCall) {
      throw new Error('No active call');
    }

    try {
      const isMuted = await this.currentCall.toggleAudioMute();
      this.emit('call.muted', { id: this.currentCall.id, muted: isMuted });
      return isMuted;
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
      const isOnHold = await this.currentCall.toggleHold();
      this.emit('call.hold', { id: this.currentCall.id, onHold: isOnHold });
      return isOnHold;
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
      await this.currentCall.sendDTMF(digit);
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

  disconnect(): void {
    if (this.currentCall) {
      this.currentCall.hangup().catch(console.error);
    }
    if (this.client) {
      this.client.offline();
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