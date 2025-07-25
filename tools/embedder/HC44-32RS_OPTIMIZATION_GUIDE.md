# HC44-32rs Azure VM Optimization Guide

This guide provides specific configuration recommendations for running the EPIC.search Embedder on Azure HC44-32rs virtual machines.

## VM Specifications
- **vCPUs**: 32 cores
- **RAM**: 352GB
- **Storage**: Premium SSD recommended
- **Network**: Accelerated networking enabled

## Optimized Configuration

### Environment Variables (.env)
```bash
# Document processing concurrency (intelligent auto-configuration)
FILES_CONCURRENCY_SIZE=auto  # Uses 16 processes (half cores) for optimal performance

# Keyword extraction threads per document (intelligent auto-configuration)  
KEYWORD_EXTRACTION_WORKERS=auto  # Uses 2 threads per process for KeyBERT optimization

# Database batch size (increased for high RAM)
CHUNK_INSERT_BATCH_SIZE=50
```

### Auto-Configuration Options
The embedder now supports intelligent auto-configuration:

**FILES_CONCURRENCY_SIZE:**
- `auto` - 16 processes (half cores for 16+ CPU systems) - **Recommended for HC44-32rs**
- `auto-full` - 32 processes (all cores) - Use if you have optimized I/O
- `auto-conservative` - 8 processes (quarter cores) - Use for shared environments
- Integer value - Manual override

**KEYWORD_EXTRACTION_WORKERS:**
- `auto` - 2 threads per process (optimized for KeyBERT bottleneck) - **Recommended**
- `auto-aggressive` - 4 threads per process (higher parallelism)
- `auto-conservative` - 1 thread per process (minimal contention)
- Integer value - Manual override

### Performance Characteristics
- **Document Workers**: 16 (optimized for HC44-32rs)
- **Keyword Threads per Document**: 2 (KeyBERT bottleneck optimization)
- **Total Concurrent Threads**: 32 (matches vCPU count for 100% utilization)
- **Database Connections**: 16 base + 32 overflow = 48 max
- **Memory Usage**: ~75-150GB typical, 200GB+ peak

## Resource Utilization

### CPU Usage

- Target: 95-100% CPU utilization during keyword extraction (the bottleneck)
- Process-level parallelism: 16 documents simultaneously  
- Thread-level parallelism: 2 keyword extraction threads per document
- Total concurrent threads: 32 (matches vCPU count for optimal efficiency)
- **Key improvement**: Eliminates thread contention from previous 128-thread configuration

### Memory Usage
- Each document process: ~4-8GB RAM
- Model loading: ~2-4GB per process
- Vector storage: Variable based on document size
- Buffer space: 50GB+ recommended

### Database Performance

- Connection pool optimized for 16 concurrent processes (reduced from 32)
- Batch inserts of 50 chunks (vs default 25) to leverage high RAM
- HNSW indexes for fast semantic search
- **Improvement**: Reduced database connection pressure

## Monitoring and Tuning

### Key Metrics to Monitor
```bash
# CPU utilization should be 85-95%
htop or top

# Memory usage should be under 300GB
free -h

# Database connection count
SELECT count(*) FROM pg_stat_activity WHERE application_name = 'epic_embedder_hc44rs';
```

### Performance Tuning

With the new auto-configuration (`FILES_CONCURRENCY_SIZE=auto` and `KEYWORD_EXTRACTION_WORKERS=auto`), 
manual tuning is rarely needed. However, if you experience issues:

**KeyBERT bottleneck persists**: Try `KEYWORD_EXTRACTION_WORKERS=auto-conservative` (1 thread per process)
**Low CPU utilization**: Try `FILES_CONCURRENCY_SIZE=auto-full` (32 processes) 
**Memory pressure**: Reduce `CHUNK_INSERT_BATCH_SIZE` to 25-35
**Database timeouts**: Check network latency and database server capacity
**Resource contention**: Try `FILES_CONCURRENCY_SIZE=auto-conservative` (8 processes)

## Expected Performance

### Typical Throughput
- **Small documents** (1-10 pages): 2-5 documents/second
- **Medium documents** (10-100 pages): 0.5-2 documents/second  
- **Large documents** (100+ pages): 0.1-0.5 documents/second

### Processing Time Estimates
- **1,000 small documents**: 5-10 minutes
- **1,000 medium documents**: 15-30 minutes
- **1,000 large documents**: 45-90 minutes

## Best Practices

### 1. Database Server
- Use Azure Database for PostgreSQL with 8+ vCPUs
- Enable connection pooling (pgbouncer recommended)
- Monitor connection count and query performance

### 2. Storage
- Use Premium SSD for temporary file storage
- Enable accelerated networking for Azure VMs
- Consider proximity placement groups for DB and VM

### 3. Monitoring
- Use Azure Monitor for VM metrics
- Set up alerts for high memory/CPU usage
- Monitor database performance counters

### 4. Scaling
- HC44-32rs is ideal for 10,000+ document workloads
- For smaller workloads, consider HC16rs (16 vCPUs)
- For massive workloads (100,000+ docs), consider multiple HC44-32rs instances

## Troubleshooting

### Common Issues
**OutOfMemoryError**: Reduce batch size or keyword workers
**Database connection timeouts**: Increase connection pool or database capacity
**Slow processing**: Check disk I/O and network latency
**Model loading failures**: Ensure sufficient disk space for model cache

### Performance Validation
Run a test with a known dataset:
```bash
python main.py --shallow 100 --project_id <test_project_id>
```

Expected results on HC44-32rs with auto-configuration:
- CPU usage: 95-100% during keyword extraction
- Memory usage: 75-150GB (reduced from previous 150-250GB)
- Processing rate: 3-10x faster than manual configuration
- Concurrent operations: 32 threads (optimized vs previous 128 threads)
