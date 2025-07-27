import React, { useState, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Chip,
  Stack,
  Alert,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Delete,
  Visibility,
  Search,
  CloudUpload,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { documentsService } from '../services/api';
import { Document } from '../types';

export const DocumentsTab: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    title: '',
    category: '',
    file: null as File | null,
  });

  // Fetch documents
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', selectedCategory],
    queryFn: () => documentsService.listDocuments(selectedCategory || undefined),
  });

  // Upload document mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadForm.file || !uploadForm.title) {
        throw new Error('Please provide both file and title');
      }
      
      const formData = new FormData();
      formData.append('file', uploadForm.file);
      formData.append('title', uploadForm.title);
      if (uploadForm.category) {
        formData.append('category', uploadForm.category);
      }
      
      return documentsService.uploadDocument(formData);
    },
    onSuccess: () => {
      enqueueSnackbar('Document uploaded successfully', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      handleCloseUploadDialog();
    },
    onError: (error: any) => {
      enqueueSnackbar(error.message || 'Failed to upload document', { variant: 'error' });
    },
  });

  // Delete document mutation
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentsService.deleteDocument(documentId),
    onSuccess: () => {
      enqueueSnackbar('Document deleted successfully', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: () => {
      enqueueSnackbar('Failed to delete document', { variant: 'error' });
    },
  });

  // Search documents mutation
  const searchMutation = useMutation({
    mutationFn: () => 
      documentsService.searchDocuments({
        query: searchQuery,
        category: selectedCategory || undefined,
        limit: 10,
      }),
    onSuccess: (results) => {
      enqueueSnackbar(`Found ${results.length} matching documents`, { variant: 'info' });
    },
    onError: () => {
      enqueueSnackbar('Search failed', { variant: 'error' });
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadForm(prev => ({
        ...prev,
        file,
        title: prev.title || file.name.split('.')[0],
      }));
    }
  };

  const handleUpload = () => {
    uploadMutation.mutate();
  };

  const handleDelete = (documentId: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate(documentId);
    }
  };

  const handleViewDocument = async (doc: Document) => {
    try {
      const fullDoc = await documentsService.getDocument(doc.document_id);
      setSelectedDocument(fullDoc);
    } catch (error) {
      enqueueSnackbar('Failed to load document', { variant: 'error' });
    }
  };

  const handleSearch = () => {
    if (searchQuery.trim()) {
      searchMutation.mutate();
    }
  };

  const handleCloseUploadDialog = () => {
    setUploadDialogOpen(false);
    setUploadForm({
      title: '',
      category: '',
      file: null,
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const categories = ['Support', 'Policy', 'Technical', 'FAQ', 'Training'];

  // Filter documents based on search results if available
  const displayDocuments = searchMutation.data || documents;

  return (
    <>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Document Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload and manage documents for AI-powered assistance
        </Typography>
      </Box>

      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
            >
              <MenuItem value="">All</MenuItem>
              {categories.map(cat => (
                <MenuItem key={cat} value={cat}>{cat}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            sx={{ flex: 1 }}
          />

          <Button
            variant="outlined"
            startIcon={<Search />}
            onClick={handleSearch}
            disabled={!searchQuery.trim() || searchMutation.isPending}
          >
            Search
          </Button>

          <Button
            variant="contained"
            startIcon={<CloudUpload />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Document
          </Button>
        </Stack>
      </Paper>

      <Paper elevation={2}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Content Preview</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : displayDocuments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    No documents found
                  </TableCell>
                </TableRow>
              ) : (
                displayDocuments.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((doc) => (
                  <TableRow key={doc.document_id} hover>
                    <TableCell>{doc.title}</TableCell>
                    <TableCell>
                      {doc.category && (
                        <Chip label={doc.category} size="small" />
                      )}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 400 }}>
                      <Typography variant="body2" noWrap>
                        {doc.content}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        onClick={() => handleViewDocument(doc)}
                        title="View"
                      >
                        <Visibility />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(doc.document_id)}
                        title="Delete"
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={displayDocuments.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
        />
      </Paper>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={handleCloseUploadDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Document</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="Document Title"
              value={uploadForm.title}
              onChange={(e) => setUploadForm(prev => ({ ...prev, title: e.target.value }))}
              fullWidth
              required
            />

            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={uploadForm.category}
                onChange={(e) => setUploadForm(prev => ({ ...prev, category: e.target.value }))}
                label="Category"
              >
                <MenuItem value="">None</MenuItem>
                {categories.map(cat => (
                  <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.pdf,.doc,.docx"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <Button
                variant="outlined"
                startIcon={<UploadIcon />}
                onClick={() => fileInputRef.current?.click()}
                fullWidth
              >
                {uploadForm.file ? uploadForm.file.name : 'Select File'}
              </Button>
              {uploadForm.file && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Size: {(uploadForm.file.size / 1024).toFixed(2)} KB
                </Typography>
              )}
            </Box>

            {uploadMutation.isError && (
              <Alert severity="error">
                Failed to upload document. Please try again.
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUploadDialog}>Cancel</Button>
          <Button
            onClick={handleUpload}
            variant="contained"
            disabled={!uploadForm.file || !uploadForm.title || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* View Document Dialog */}
      <Dialog
        open={!!selectedDocument}
        onClose={() => setSelectedDocument(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedDocument && (
          <>
            <DialogTitle>
              {selectedDocument.title}
              {selectedDocument.category && (
                <Chip
                  label={selectedDocument.category}
                  size="small"
                  sx={{ ml: 2 }}
                />
              )}
            </DialogTitle>
            <DialogContent dividers>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {selectedDocument.content}
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedDocument(null)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </>
  );
};