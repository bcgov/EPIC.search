# PGVector Swap and Benchmarks

For this round of performance tests, the VectorScale extension has been swapped with PGVector and the database is now running on a Managed PostgreSQL flexible server setup (single instance) with the following specifications:

| Specification               | Details                      |
|-----------------------------|------------------------------|
| **Instance Type**           | General Purpose, D4s_v3      |
| **vCPUs**                   | 4                            |
| **RAM (GiB)**               | 16                           |
| **Storage (GiB)**           | 1024                         |
| **Database Type**           | Managed PostgreSQL flexible server |

## Embedding Performance

The embedder was used to process the Coyote Hydrogen Project documents:

```json
{
    "message": "Processing completed", 
    "results": [
        {
            "project_name": "Coyote Hydrogen Project", 
            "duration_seconds": 112.541351
        }
    ]
}
```

This represents a significant improvement compared to the previous setup which took around 3103 seconds (~52 minutes) with the initial Basic B3 compute, and 111 seconds with the F8s_v2 compute optimized VM.

## Testing

**Basic Test:**
Question: Who is the main proponent of the BC Hydrogen project?
Test Conditions: The same documents are embedded into the Vector DB as in the previous tests.

**Result 1:**
Answer: The main proponent of the BC Hydrogen Project is Canada Fortescue Future Industries. This project aims to construct and operate a hydrogen production facility in Prince George, British Columbia (BC). The Canadian government has recently adopted policies related to hydrogen development, including the Canada Hydrogen Policy and the British Columbia Hydrogen Strategy. Both federal and provincial governments have expressed interest in supporting this project.

```json
"metrics": {
    "start_time": "2025-05-09 22:46:27 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 24540.91,
    "search_breakdown": {
        "keyword_search_ms": 10312.48,
        "semantic_search_ms": 6033.69,
        "combine_results_ms": 0.43,
        "deduplication_ms": 0.68,
        "reranking_ms": 8112.61,
        "formatting_ms": 0.18,
        "total_search_ms": 24460.15
    },
    "llm_time_ms": 4763.76,
    "total_time_ms": 29304.74
}
```

**Result 2:**
Answer: The main proponent of the BC Hydrogen project is Canada Fortescue Future Industries. This company has been involved in various aspects of the project, including the environmental assessment and the procurement requirements for materials, goods, and services. The Canadian government has also recently adopted policies related to hydrogen development, which have made this project more attractive to the industry.

```json
"metrics": {
    "start_time": "2025-05-09 22:54:28 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 24309.35,
    "search_breakdown": {
        "keyword_search_ms": 10094.19,
        "semantic_search_ms": 6806.33,
        "combine_results_ms": 0.45,
        "deduplication_ms": 0.65,
        "reranking_ms": 7317.49,
        "formatting_ms": 0.18,
        "total_search_ms": 24219.37
    },
    "llm_time_ms": 45032.74,
    "total_time_ms": 69342.16
}
```

**Result 3:**
Answer: The main proponent of the BC Hydrogen Project is Canada Fortescue Future Industries. This company has been involved in the development and construction of several hydrogen projects, including the Coyote Hydrogen Project. The project aims to develop a new energy infrastructure that can be used for both domestic and export markets, with the goal of reducing carbon emissions.

```json
"metrics": {
    "start_time": "2025-05-09 22:56:09 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 20101.34,
    "search_breakdown": {
        "keyword_search_ms": 7836.55,
        "semantic_search_ms": 5615.51,
        "combine_results_ms": 0.42,
        "deduplication_ms": 0.56,
        "reranking_ms": 6549.86,
        "formatting_ms": 0.16,
        "total_search_ms": 20003.15
    },
    "llm_time_ms": 4272.8,
    "total_time_ms": 24374.2
}
```

## Performance Comparison

### Vector Database Performance

| Metric | VectorScale (VM) | PGVector (Managed) |
|--------|------------------|-------------------|
| Average Search Time | ~25 sec | ~23 sec |
| Storage Cost | CA $208.05/month | Premium Tier pricing |
| Setup Complexity | Manual VM setup | Managed service |
| Maintenance | Manual | Automated by Azure |

### Embedding Performance PGVector

| Metric | Initial Setup (Basic B3) | VM Setup (F8s_v2) | PGVector (Current) |
|--------|--------------------------|-------------------|-------------------|
| Processing Time | ~3103 sec | ~111 sec | ~112.5 sec |
| Cost | CAD $65.70/month | CAD $346.75/month | Included in managed DB costs |

## Summary

The PGVector extension on a Managed PostgreSQL flexible server provides comparable performance to the previous VectorScale setup while offering advantages in terms of maintenance and manageability. The embedding performance remains excellent at around 112 seconds for processing the Coyote Hydrogen Project documents, which is a significant improvement over the initial setup that took over 50 minutes.

The search performance is generally consistent with the previous setup, with search times averaging around 23 seconds across the tests. The LLM response time varies considerably (from ~4 seconds to ~45 seconds in our tests), which appears to be due to variations in resource availability or the complexity of the generated response.

### Cost-Benefit Analysis

Moving to a managed PostgreSQL service with PGVector offers several benefits:

1. Reduced maintenance overhead - Azure handles database maintenance tasks
2. Improved reliability with built-in high availability features
3. Automatic backups and patching
4. Streamlined scaling options

These advantages come at a cost comparable to the self-managed VM solution but with less operational overhead.

## Next Steps

1. Consider testing with larger document sets to evaluate performance at scale
2. Evaluate the impact of scaling up the managed PostgreSQL instance for improved search performance
3. Compare the cost-performance ratio of different instance sizes
4. Explore options for optimizing PGVector indexing for faster semantic search
