// SignalWire SDK Type Definitions
declare global {
  interface Window {
    SignalWire: SignalWireNamespace;
  }
  const SignalWire: SignalWireNamespace;
}

export interface SignalWireClient {
  dial(params: DialParams): Promise<FabricRoomSession>;
  online(params?: OnlineParams): Promise<void>;
  offline(): Promise<void>;
  disconnect(): Promise<void>;
  on(event: string, handler: Function): void;
  off(event: string, handler: Function): void;
}

export interface DialParams {
  to: string;
  audio?: boolean | MediaTrackConstraints;
  video?: boolean | MediaTrackConstraints;
  rootElement?: HTMLElement;
  userVariables?: Record<string, any>;
  negotiateAudio?: boolean;
  negotiateVideo?: boolean;
}

export interface OnlineParams {
  incomingCallHandlers?: {
    all?: (notification: IncomingCallNotification) => void | Promise<void>;
    pushNotification?: (notification: IncomingCallNotification) => void | Promise<void>;
  };
}

export interface IncomingCallNotification {
  invite: FabricRoomSession;
}

export interface FabricRoomSession {
  id: string;
  state?: string;
  memberId?: string;
  nodeId?: string;
  roomId?: string;
  roomSessionId?: string;
  
  // Media control methods
  audioMute(): Promise<void>;
  audioUnmute(): Promise<void>;
  videoMute(): Promise<void>;
  videoUnmute(): Promise<void>;
  deaf(): Promise<void>;
  undeaf(): Promise<void>;
  
  // Call control methods
  start(): Promise<void>;
  leave(): Promise<void>;
  hangup?(): Promise<void>; // Not all SDK versions have this
  hold(): Promise<void>;
  unhold(): Promise<void>;
  sendDigits(dtmf: string): Promise<void>;
  
  // Media device methods
  updateCamera(constraints: MediaTrackConstraints): Promise<void>;
  updateMicrophone(constraints: MediaTrackConstraints): Promise<void>;
  
  // Event methods
  on(event: FabricRoomSessionEvents | string, handler: Function): void;
  off(event: FabricRoomSessionEvents | string, handler: Function): void;
  once(event: FabricRoomSessionEvents | string, handler: Function): void;
  
  // Incoming call methods (for invite objects)
  accept?(params?: { rootElement?: HTMLElement }): Promise<FabricRoomSession>;
  reject?(): Promise<void>;
  
  // Additional properties from invite
  details?: {
    caller_id_number?: string;
    caller_id_name?: string;
  };
}

export type FabricRoomSessionEvents = 
  | 'room.subscribed'
  | 'room.updated'
  | 'member.joined'
  | 'member.left'
  | 'member.updated'
  | 'member.updated.audioMuted'
  | 'member.updated.videoMuted'
  | 'member.talking'
  | 'layout.changed'
  | 'destroy'
  | 'state'
  | 'media.connected'
  | 'media.disconnected'
  | 'media.reconnecting'
  | 'verto.display'
  | 'track';

export interface SignalWireNamespace {
  SignalWire?(params: { token: string; rootElement?: HTMLElement }): Promise<SignalWireClient>;
  (params: { token: string; rootElement?: HTMLElement }): Promise<SignalWireClient>;
  Fabric?: {
    Client?: new (params: { token: string; rootElement?: HTMLElement }) => SignalWireClient;
  };
}

