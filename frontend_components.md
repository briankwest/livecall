# React Frontend Components Design

## Component Hierarchy

```
App
├── Layout
│   ├── Header
│   └── Sidebar
├── Pages
│   ├── Dashboard
│   │   ├── ActiveCallsList
│   │   └── CallStatistics
│   ├── LiveCall
│   │   ├── CallInfo
│   │   ├── TranscriptionPanel
│   │   ├── AIAssistancePanel
│   │   └── DocumentViewer
│   └── CallHistory
│       ├── CallsTable
│       └── CallDetails
└── Components
    ├── Common
    │   ├── LoadingSpinner
    │   ├── ErrorBoundary
    │   └── NotificationToast
    └── Call
        ├── TranscriptionBubble
        ├── DocumentCard
        └── SuggestionCard
```

## Key Components

### 1. LiveCall Component
```typescript
interface LiveCallProps {
  callId: string;
}

// Features:
- Real-time transcription display
- AI suggestions sidebar
- Document preview modal
- Call controls (mute, hold, end)
- Listening mode toggle
```

### 2. TranscriptionPanel
```typescript
interface TranscriptionPanelProps {
  transcriptions: Transcription[];
  isLive: boolean;
}

// Features:
- Auto-scroll to latest
- Speaker identification
- Timestamp display
- Search/filter capability
- Export functionality
```

### 3. AIAssistancePanel
```typescript
interface AIAssistancePanelProps {
  suggestions: AISuggestion[];
  onDocumentClick: (docId: string) => void;
}

// Features:
- Relevance-sorted documents
- Preview on hover
- Quick actions (open, dismiss)
- Feedback buttons
- Context highlighting
```

### 4. DocumentViewer
```typescript
interface DocumentViewerProps {
  documentId: string;
  highlightText?: string;
}

// Features:
- PDF/Markdown rendering
- Text highlighting
- Navigation breadcrumbs
- Copy to clipboard
- Full-screen mode
```

## State Management

### Context Providers
```typescript
// WebSocketContext
- Socket connection state
- Event subscriptions
- Reconnection status

// CallContext  
- Active call data
- Transcriptions
- AI suggestions
- Call statistics

// UserContext
- Agent information
- Preferences
- Permissions
```

## UI/UX Features
1. **Dark mode support**
2. **Responsive design** (desktop-first)
3. **Keyboard shortcuts**
4. **Accessibility** (WCAG 2.1 AA)
5. **Real-time indicators**
6. **Performance optimizations**