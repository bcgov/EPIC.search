import { Paper, Container } from "@mui/material";

export default function NoRoles() {
  return (
    <Container id="Error404">
      <Paper
        elevation={3}
        sx={{
          padding: "1rem",
          marginTop: "2rem",
          textAlign: "center",
        }}
      >
        <h1>Unauthorized</h1>
        <p>You need to request access from the administrator.</p>
      </Paper>
    </Container>
  );
}
