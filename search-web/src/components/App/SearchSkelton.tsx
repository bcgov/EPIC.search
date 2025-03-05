import { Grid, Skeleton } from "@mui/material";

const SearchSkelton = () => {
  return (
    <>
      <Skeleton
        variant="rounded"
        height={100}
        width="100%"
        sx={{ my: 2, borderRadius: 4 }}
      />
      <Grid container spacing={2}>
        <Grid item xs={12} md={6} lg={4}>
          <Skeleton variant="rounded" height={200} sx={{ borderRadius: 4 }} />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <Skeleton variant="rounded" height={200} sx={{ borderRadius: 4 }} />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <Skeleton variant="rounded" height={200} sx={{ borderRadius: 4 }} />
        </Grid>
      </Grid>
    </>
  );
};

export default SearchSkelton;
