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
# Document processing concurrency (auto-detects all 32 cores)
# FILES_CONCURRENCY_SIZE=auto

# Keyword extraction threads per document (conservative for CPU efficiency)
KEYWORD_EXTRACTION_WORKERS=4

# Database batch size (increased for high RAM)
CHUNK_INSERT_BATCH_SIZE=50
```

### Performance Characteristics
- **Document Workers**: 32 (one per vCPU)
- **Keyword Threads per Document**: 4
- **Total Concurrent Threads**: 128 (4 threads per vCPU)
- **Database Connections**: 32 base + 64 overflow = 96 max
- **Memory Usage**: ~150-200GB typical, 300GB+ peak

## Resource Utilization

### CPU Usage
- Target: 85-95% CPU utilization
- Process-level parallelism: 32 documents simultaneously
- Thread-level parallelism: 4 keyword extraction threads per document
- Total theoretical throughput: 128 concurrent operations

### Memory Usage
- Each document process: ~4-8GB RAM
- Model loading: ~2-4GB per process
- Vector storage: Variable based on document size
- Buffer space: 50GB+ recommended

### Database Performance
- Connection pool optimized for 32 concurrent processes
- Batch inserts of 50 chunks (vs default 25) to leverage high RAM
- HNSW indexes for fast semantic search

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
If you experience:

**High CPU but low throughput**: Reduce `KEYWORD_EXTRACTION_WORKERS` to 2-3
**Memory pressure**: Reduce `CHUNK_INSERT_BATCH_SIZE` to 25-35
**Database timeouts**: Check network latency and database server capacity
**Low CPU utilization**: Increase `KEYWORD_EXTRACTION_WORKERS` to 6-8

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

Expected results on HC44-32rs:
- CPU usage: 85-95%
- Memory usage: 150-250GB
- Processing rate: 1-3 documents/second (depending on size)
