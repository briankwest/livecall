import React from 'react';
import { Box, Button, Typography } from '@mui/material';

function App() {
  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4">Test App</Typography>
      <Button 
        variant="contained" 
        onClick={() => {
          console.log('Button clicked!');
          alert('Button clicked!');
        }}
      >
        Click Me
      </Button>
    </Box>
  );
}

export default App;