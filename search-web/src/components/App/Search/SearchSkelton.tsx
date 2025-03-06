import { Grid, Skeleton, Typography } from "@mui/material";
import loading from "@/assets/images/loading.gif";
const SearchSkelton = () => {
  return (
    <>
      <img src={loading} height={48} style={{ margin: "16px auto" }} />
      <Typography variant="body2" sx={{ textAlign: "center" }} color="primary">
        please wait while we search for your documents...
      </Typography>
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
