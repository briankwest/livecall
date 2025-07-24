import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  IconButton,
  Collapse,
  Stack,
} from '@mui/material';
import {
  ThumbUp,
  ThumbDown,
  ExpandMore,
  ExpandLess,
  Article,
} from '@mui/icons-material';
import { Document } from '../../types';

interface AIAssistancePanelProps {
  suggestions: Document[];
  summary?: string;
  topics?: string[];
  onDocumentClick: (docId: string) => void;
  onFeedback: (docId: string, helpful: boolean) => void;
}

export const AIAssistancePanel: React.FC<AIAssistancePanelProps> = ({
  suggestions,
  summary,
  topics,
  onDocumentClick,
  onFeedback,
}) => {
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());

  const toggleExpanded = (docId: string) => {
    setExpandedDocs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  return (
    <Paper
      elevation={2}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">AI Assistance</Typography>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {summary && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="subtitle2" color="primary" gutterBottom>
                Context Summary
              </Typography>
              <Typography variant="body2">{summary}</Typography>
              {topics && topics.length > 0 && (
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  {topics.map((topic, index) => (
                    <Chip key={index} label={topic} size="small" />
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        )}

        {suggestions.length === 0 ? (
          <Typography color="text.secondary" align="center">
            No document suggestions yet...
          </Typography>
        ) : (
          <Stack spacing={2}>
            {suggestions.map((doc) => (
              <Card key={doc.document_id}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Article color="primary" />
                    <Typography variant="subtitle1" sx={{ flex: 1 }}>
                      {doc.title}
                    </Typography>
                    {doc.similarity && (
                      <Chip
                        label={`${Math.round(doc.similarity * 100)}%`}
                        size="small"
                        color="success"
                      />
                    )}
                  </Box>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    {expandedDocs.has(doc.document_id)
                      ? doc.content
                      : doc.content.substring(0, 150) + '...'}
                  </Typography>

                  {doc.category && (
                    <Chip
                      label={doc.category}
                      size="small"
                      variant="outlined"
                      sx={{ mt: 1 }}
                    />
                  )}
                </CardContent>

                <CardActions>
                  <Button
                    size="small"
                    onClick={() => onDocumentClick(doc.document_id)}
                  >
                    View Full
                  </Button>
                  <IconButton
                    size="small"
                    onClick={() => toggleExpanded(doc.document_id)}
                  >
                    {expandedDocs.has(doc.document_id) ? (
                      <ExpandLess />
                    ) : (
                      <ExpandMore />
                    )}
                  </IconButton>
                  <Box sx={{ flex: 1 }} />
                  <IconButton
                    size="small"
                    color="success"
                    onClick={() => onFeedback(doc.document_id, true)}
                  >
                    <ThumbUp />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => onFeedback(doc.document_id, false)}
                  >
                    <ThumbDown />
                  </IconButton>
                </CardActions>
              </Card>
            ))}
          </Stack>
        )}
      </Box>
    </Paper>
  );
};