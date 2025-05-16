# PGVector Swap and Benchmarks

For this round of performance tests, the VectorScale extension has been swapped with PGVector and the database is now running on a Managed PostgreSQL flexible server setup (single instance) with standard tier specifications:

| Specification               | Details                      |
|-----------------------------|------------------------------|
| **Instance Type**           | General Purpose              |
| **Compute Tier**            | Standard                     |
| **Memory Tier**             | Standard                     |
| **Storage Type**            | Premium                      |
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

## Scaled-up Test

For the next set of tests, we scaled up both the model host and the vector API to analyze performance improvements:

| Component | Initial Setup | Scaled-up Setup |
|-----------|--------------|-----------------|
| Vector API | Basic Tier | Premium Tier |
| Model Host | Standard Compute | High-Performance Compute |
| Relative Cost | 1.0x | ~5.2x |
| Performance Impact | Baseline | Significant Improvement |

### Test Question

Who is the main proponent of the BC hydrogen project?

### Result 1

Answer: The main proponent of the BC Hydrogen Project is Canada Fortescue Future Industries (CFFI). This company has been involved in multiple projects related to hydrogen and green energy, including the Coyote Hydrogen Project. The project aims to develop a new hydrogen production facility in Prince George, British Columbia, with the goal of providing clean hydrogen for transportation and distribution purposes. CFFI is responsible for overseeing the development and implementation of the project, as well as engaging with local communities and stakeholders.

```json
"metrics": {
    "start_time": "2025-05-12 18:37:15 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 4342.49,
    "search_breakdown": {
        "keyword_search_ms": 1201.06,
        "semantic_search_ms": 1188.69,
        "combine_results_ms": 0.38,
        "deduplication_ms": 0.54,
        "reranking_ms": 1866.0,
        "formatting_ms": 0.15,
        "total_search_ms": 4256.89
    },
    "llm_time_ms": 2478.92,
    "total_time_ms": 6821.47
}
```

### Result 2

Answer: Based on the information provided, the main proponent of the BC hydrogen project is Fortescue Canada. The Canadian government and British Columbia have recently adopted policies related to hydrogen development, which includes the Project Coyote Hydrogen Project. Fortescue Canada is the proposed project's proponent, with the goal of developing a green hydrogen economy in Prince George, British Columbia.

```json
"metrics": {
    "start_time": "2025-05-12 18:38:00 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 4261.49,
    "search_breakdown": {
        "keyword_search_ms": 1173.43,
        "semantic_search_ms": 1162.26,
        "combine_results_ms": 0.38,
        "deduplication_ms": 0.52,
        "reranking_ms": 1822.46,
        "formatting_ms": 0.17,
        "total_search_ms": 4159.28
    },
    "llm_time_ms": 1867.3,
    "total_time_ms": 6128.86
}
```

### Result 3

Answer: The main proponent of the BC hydrogen project is Fortescue Canada. The Canadian government, specifically the Government of British Columbia and the City of Prince George, have recently adopted policies related to hydrogen development. These policies aim to achieve net-zero emissions by 2050 and position Canada as a global leader in clean renewable fuels. Fortescue Canada is not aware of any government policies that may be incompatible with the development of the Project.

```json
"metrics": {
    "start_time": "2025-05-12 18:38:33 UTC",
    "get_synthesizer_time": 0.0,
    "search_time_ms": 5513.14,
    "search_breakdown": {
        "keyword_search_ms": 2073.71,
        "semantic_search_ms": 1008.31,
        "combine_results_ms": 0.57,
        "deduplication_ms": 0.8,
        "reranking_ms": 2346.4,
        "formatting_ms": 0.17,
        "total_search_ms": 5430.07
    },
    "llm_time_ms": 2247.35,
    "total_time_ms": 7760.56
}
```

## Performance Comparison Across All Configurations

### Hardware Configurations

| Configuration | Database | Vector API | Model Host | 
|---------------|----------|------------|------------|
| Initial Setup | Self-managed VM | Basic Tier | Standard Compute |
| PGVector Base | Managed Service | Basic Tier | Standard Compute |
| Scaled-up Setup | Managed Service | Premium Tier | High-Performance Compute |

### Search Performance

| Metric | VectorScale (Initial) | PGVector (Base) | PGVector (Scaled-up) |
|--------|---------------------|-----------------|----------------------|
| Average Search Time | ~25 sec | ~23 sec | ~4.7 sec |
| Average Total Response Time | ~41 sec | ~41 sec | ~6.9 sec |
| Keyword Search Time | ~9.4 sec | ~9.1 sec | ~1.5 sec |
| Semantic Search Time | ~6.1 sec | ~6.2 sec | ~1.1 sec |
| Reranking Time | ~7.3 sec | ~7.3 sec | ~2.0 sec |
| LLM Processing Time | ~18 sec | ~18 sec | ~2.2 sec |

### Cost Analysis

| Component | VectorScale (Initial) | PGVector (Base) | PGVector (Scaled-up) |
|-----------|----------------------|-----------------|----------------------|
| Database Cost | CA $208.05/month | CA $231.75/month | CA $231.75/month |
| Vector API Cost | CA $65.70/month | CA $65.70/month | CA $342.30/month |
| Model Host Cost | CA $120.45/month | CA $173.38/month | CA $693.50/month |
| **Total Monthly Cost** | **CA $394.20/month** | **CA $470.83/month** | **CA $1,267.55/month** |
| Performance Gain | Baseline | Minimal | 5.9x faster |
| Cost-Performance Ratio | 1.0x | 0.84x | 1.83x |

## Summary

The PGVector extension on a Managed PostgreSQL flexible server provides comparable performance to the previous VectorScale setup while offering advantages in terms of maintenance and manageability in our base configuration. The embedding performance remains excellent at around 112 seconds for processing the Coyote Hydrogen Project documents, which is a significant improvement over the initial setup that took over 50 minutes.

In the base configuration, search performance was generally consistent with the previous setup, with search times averaging around 23 seconds across the tests. The LLM response time varied considerably (from ~4 seconds to ~45 seconds in our tests), which appears to be due to variations in resource availability or the complexity of the generated response.

When scaling up both the Vector API and the model host VM to premium tiers, we observed dramatic performance improvements. The average search time decreased from ~23 seconds to just ~4.7 seconds, representing a nearly 5x improvement. Total response time including LLM processing improved from ~41 seconds to ~6.9 seconds, a 6x improvement. This demonstrates that the system can be effectively scaled for high-performance requirements.

### Cost-Benefit Analysis

Moving to a managed PostgreSQL service with PGVector offers several benefits:

1. Reduced maintenance overhead - Azure handles database maintenance tasks
2. Improved reliability with built-in high availability features
3. Automatic backups and patching
4. Streamlined scaling options

These advantages come at a cost comparable to the self-managed VM solution but with less operational overhead in the base configuration. The scaled-up configuration provides dramatically improved performance at a higher cost, resulting in a better overall cost-performance ratio compared to the baseline VectorScale setup.

## Next Steps

1. Consider testing with larger document sets to evaluate performance at scale
2. Further analyze the impact of different PostgreSQL instance sizes on search performance
3. Compare the cost-performance ratio of different instance combinations to find an optimal balance
4. Explore options for optimizing PGVector indexing for even faster semantic search
5. Evaluate the impact of using higher-tier Azure OpenAI models for potentially improved answer quality
6. Consider implementing a more dynamic scaling approach based on workload demands
