import { createFileRoute } from '@tanstack/react-router'
import { Container, Typography } from '@mui/material'

function TestPage() {
  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h2" gutterBottom>
        Test Route - No Auth Required
      </Typography>
      <Typography variant="body1">
        If you can see this page, the routing is working without authentication.
      </Typography>
    </Container>
  );
}

export const Route = createFileRoute('/test-no-auth')({
  component: TestPage,
})
