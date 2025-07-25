import React, { useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Chip,
  Stack,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  SentimentVerySatisfied,
  SentimentNeutral,
  SentimentVeryDissatisfied,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
} from '@mui/icons-material';
import { Transcription } from '../../types';

interface SentimentSummaryProps {
  transcriptions: Transcription[];
}

interface SentimentAnalysis {
  overall: 'positive' | 'neutral' | 'negative';
  score: number;
  trend: 'improving' | 'declining' | 'stable';
  counts: { positive: number; neutral: number; negative: number };
  recentSentiments: string[];
}

export const SentimentSummary: React.FC<SentimentSummaryProps> = ({
  transcriptions,
}) => {
  const calculateSentimentData = (speakerTranscriptions: Transcription[]): SentimentAnalysis => {
    if (speakerTranscriptions.length === 0) {
      return {
        overall: 'neutral',
        score: 0.5,
        trend: 'stable',
        counts: { positive: 0, neutral: 0, negative: 0 },
        recentSentiments: [],
      };
    }

    // Count sentiments
    const counts = {
      positive: 0,
      neutral: 0,
      negative: 0,
    };

    let totalScore = 0;
    speakerTranscriptions.forEach(t => {
      if (t.sentiment === 'positive') counts.positive++;
      else if (t.sentiment === 'negative') counts.negative++;
      else counts.neutral++;
      
      totalScore += t.sentiment_score || 0.5;
    });

    const avgScore = totalScore / speakerTranscriptions.length;

    // Determine overall sentiment
    let overall: 'positive' | 'neutral' | 'negative' = 'neutral';
    if (avgScore >= 0.7) overall = 'positive';
    else if (avgScore <= 0.3) overall = 'negative';

    // Calculate trend (compare last 3 vs previous)
    let trend: 'improving' | 'declining' | 'stable' = 'stable';
    if (speakerTranscriptions.length >= 6) {
      const recent = speakerTranscriptions.slice(-3);
      const older = speakerTranscriptions.slice(-6, -3);
      
      const recentAvg = recent.reduce((sum, t) => sum + (t.sentiment_score || 0.5), 0) / recent.length;
      const olderAvg = older.reduce((sum, t) => sum + (t.sentiment_score || 0.5), 0) / older.length;
      
      if (recentAvg > olderAvg + 0.1) trend = 'improving';
      else if (recentAvg < olderAvg - 0.1) trend = 'declining';
    }

    // Get last 5 sentiments for visual indicator
    const recentSentiments = speakerTranscriptions
      .slice(-5)
      .map(t => t.sentiment || 'neutral');

    return {
      overall,
      score: avgScore,
      trend,
      counts,
      recentSentiments,
    };
  };

  const customerSentiment = useMemo(() => {
    const customerTranscriptions = transcriptions.filter(
      t => t.speaker === 'customer' && t.sentiment
    );
    return calculateSentimentData(customerTranscriptions);
  }, [transcriptions]);

  const agentSentiment = useMemo(() => {
    const agentTranscriptions = transcriptions.filter(
      t => t.speaker === 'agent' && t.sentiment
    );
    return calculateSentimentData(agentTranscriptions);
  }, [transcriptions]);

  const getSentimentIcon = (sentiment: string, size: 'small' | 'medium' = 'medium') => {
    const fontSize = size === 'small' ? 'small' : 'medium';
    switch (sentiment) {
      case 'positive':
        return <SentimentVerySatisfied fontSize={fontSize} sx={{ color: 'success.main' }} />;
      case 'negative':
        return <SentimentVeryDissatisfied fontSize={fontSize} sx={{ color: 'error.main' }} />;
      default:
        return <SentimentNeutral fontSize={fontSize} sx={{ color: 'warning.main' }} />;
    }
  };

  const getTrendIcon = () => {
    switch (customerSentiment.trend) {
      case 'improving':
        return <TrendingUp sx={{ color: 'success.main' }} />;
      case 'declining':
        return <TrendingDown sx={{ color: 'error.main' }} />;
      default:
        return <TrendingFlat sx={{ color: 'text.secondary' }} />;
    }
  };

  const getOverallColor = (sentiment: SentimentAnalysis) => {
    switch (sentiment.overall) {
      case 'positive':
        return 'success.main';
      case 'negative':
        return 'error.main';
      default:
        return 'warning.main';
    }
  };

  const renderSentimentSection = (title: string, sentiment: SentimentAnalysis, showWarning: boolean = false) => (
    <Box>
      <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
        {title}
      </Typography>

      {/* Overall Sentiment */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        {getSentimentIcon(sentiment.overall)}
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2">
            Overall: {sentiment.overall.charAt(0).toUpperCase() + sentiment.overall.slice(1)}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LinearProgress
              variant="determinate"
              value={sentiment.score * 100}
              sx={{
                height: 6,
                borderRadius: 3,
                flex: 1,
                backgroundColor: 'grey.300',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: getOverallColor(sentiment),
                },
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {Math.round(sentiment.score * 100)}%
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Sentiment Counts */}
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <Chip
          icon={<SentimentVerySatisfied />}
          label={sentiment.counts.positive}
          size="small"
          color="success"
          variant="outlined"
        />
        <Chip
          icon={<SentimentNeutral />}
          label={sentiment.counts.neutral}
          size="small"
          color="warning"
          variant="outlined"
        />
        <Chip
          icon={<SentimentVeryDissatisfied />}
          label={sentiment.counts.negative}
          size="small"
          color="error"
          variant="outlined"
        />
      </Stack>

      {/* Recent Sentiments */}
      {sentiment.recentSentiments.length > 0 && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Recent:
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
            {sentiment.recentSentiments.map((s, index) => (
              <Tooltip key={index} title={`${index + 1} messages ago`}>
                <Box>{getSentimentIcon(s, 'small')}</Box>
              </Tooltip>
            ))}
          </Box>
        </Box>
      )}

      {/* Warning for declining sentiment */}
      {showWarning && sentiment.trend === 'declining' && sentiment.overall !== 'positive' && (
        <Box
          sx={{
            mt: 1,
            p: 1,
            backgroundColor: 'error.light',
            borderRadius: 1,
            opacity: 0.8,
          }}
        >
          <Typography variant="caption" sx={{ color: 'error.dark' }}>
            ⚠️ Sentiment is declining - consider empathetic response
          </Typography>
        </Box>
      )}
    </Box>
  );

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Call Sentiment Analysis
      </Typography>

      {/* Customer Sentiment */}
      {renderSentimentSection('Customer Sentiment', customerSentiment, true)}

      <Divider sx={{ my: 2 }} />

      {/* Agent Sentiment */}
      {renderSentimentSection('Agent Sentiment', agentSentiment, false)}

      {/* Overall Call Mood */}
      {(customerSentiment.overall === 'negative' || agentSentiment.overall === 'negative') && (
        <>
          <Divider sx={{ my: 2 }} />
          <Box
            sx={{
              p: 1.5,
              backgroundColor: 'warning.light',
              borderRadius: 1,
              opacity: 0.9,
            }}
          >
            <Typography variant="body2" sx={{ color: 'warning.dark' }}>
              💡 Tip: {
                customerSentiment.overall === 'negative' && agentSentiment.overall === 'negative'
                  ? "Both parties showing negative sentiment. Consider a brief pause or topic shift."
                  : customerSentiment.overall === 'negative'
                  ? "Customer showing frustration. Maintain calm and empathetic tone."
                  : "Stay positive - your mood affects the customer experience."
              }
            </Typography>
          </Box>
        </>
      )}
    </Paper>
  );
};