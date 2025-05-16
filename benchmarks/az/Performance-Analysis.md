# EPIC.search Performance Analysis

This document analyzes the performance metrics and cost-effectiveness across different infrastructure configurations of the EPIC.search RAG application. It focuses on two key transitions:

1. Migration from VectorScale to PGVector
2. Performance testing with scaled hardware configurations to evaluate potential benefits

Note: While higher-specification hardware was tested to evaluate performance benefits, the current deployed environment runs on the base configuration. This analysis helps inform future scaling decisions.

## Architecture Evolution

```mermaid
graph TD
    subgraph Initial[Initial Setup - VectorScale]
        A1[Web UI - Basic B3] --> B1[Web API - Basic B3]
        B1 --> C1[Vector API - Basic B3]
        C1 --> D1[VectorScale DB - D4s v3 VM]
        B1 --> E1[LLM Model - P2V3]
    end

    subgraph Current[Current Deployed Setup - PGVector]
        A2[Web UI - Basic B3] --> B2[Web API - Basic B3]
        B2 --> C2[Vector API - Basic B3]
        C2 --> D2[PGVector - Managed PostgreSQL D4s_v3]
        B2 --> E2[LLM Model - F4s_v2]
    end

    subgraph Tested[Tested Scaled Configuration]
        A3[Web UI - Basic B3] --> B3[Web API - Basic B3]
        B3 --> C3[Vector API - Premium P2V3]
        C3 --> D3[PGVector - Managed PostgreSQL D4s_v3]
        B3 --> E3[LLM Model - F16s_V2]
    end
```

## Hardware Configurations Comparison

```mermaid
graph LR
    subgraph Hardware["Hardware Configurations"]
        direction LR
        
        subgraph Current["Current Deployed"]
            direction LR
            DB1[Standard Tier<br/>Database] --> SPEC1["• Standard Compute<br/>• Standard Memory<br/>• Base Storage"]
            SPEC1 --> SVC1["Services:<br/>• Basic Tier Web/API<br/>• Standard Compute Model"]
        end
        
        subgraph Tested["Tested Scaled"]
            direction LR
            DB2[Standard Tier<br/>Database] --> SPEC2["• Standard Compute<br/>• Standard Memory<br/>• Base Storage"]
            SPEC2 --> SVC2["Services:<br/>• Premium Tier API<br/>• High-Performance Model"]
        end
    end
```

### Service Tier Comparison

| Component | Current Deployed | Tested Scaled Setup |
|-----------|-----------------|-------------------|
| Database | Standard Tier | Standard Tier |
| Vector API | Basic Tier | Premium Tier |
| Model Host | Standard Compute | High-Performance Compute |
| **Scale Level** | **Base Configuration** | **Enhanced Configuration** |

## Performance Metrics

### Response Time Breakdown

```mermaid
graph LR
    subgraph Response["Response Time Components"]
        direction LR
        
        subgraph VS["VectorScale Base"]
            direction LR
            VS1["• Keyword: 7.8s<br/>• Semantic: 5.6s<br/>• Rerank: 6.5s<br/>• LLM: 4.2s"] --> VST[["Total:<br/>24.3s"]]
        end
        
        subgraph PGB["PGVector Base"]
            direction LR
            PG1["• Keyword: 7.8s<br/>• Semantic: 5.6s<br/>• Rerank: 6.5s<br/>• LLM: 4.2s"] --> PGT[["Total:<br/>24.3s"]]
        end
        
        subgraph PGS["PGVector Scaled Test"]
            direction LR
            PG2["• Keyword: 1.2s<br/>• Semantic: 1.1s<br/>• Rerank: 1.8s<br/>• LLM: 2.2s"] --> PST[["Total:<br/>6.8s"]]
        end
    end
```

### Cost vs Performance Analysis

> **Note:** The costs shown here are relative comparisons of primary component costs only. These are rough estimates that focus on the main infrastructure components. Additional costs from supporting resources like public IPs, storage, networking, monitoring, and other Azure services are not included in these comparisons.

```mermaid
graph LR
    subgraph Cost-Performance
        direction LR
        subgraph Base["Base Configurations"]
            V1[VectorScale] --> V2[1.0x cost<br/>24.3s response]
            P1[PGVector] --> P2[1.2x cost<br/>24.3s response]
        end
        
        subgraph Enhanced["Enhanced Configuration"]
            E1[PGVector Enhanced] --> E2[3.5x performance<br/>6.8s response]
        end
    end
```

## Key Performance Indicators

| Configuration | Avg Response Time | Relative Cost | Performance Gain | Cost-Performance Ratio |
|--------------|------------------|---------------|------------------|----------------------|
| VectorScale Base | 24.3s | 1.0x | 1.0x | 1.0 |
| PGVector Base | 24.3s | 1.2x | 1.0x | 0.84 |
| PGVector Scaled | 6.8s | 3.2x | 3.6x | 1.12 |

## Document Processing Performance

```mermaid
graph LR
    subgraph Processing Times
        PT1[Initial Setup] --> PT2[3103s]
        PT3[VM Setup F8s_v2] --> PT4[111s]
        PT5[PGVector Current] --> PT6[112.5s]
    end
```

## Analysis and Recommendations

### Current Performance Bottlenecks

1. **Single Instance Deployment**
   - All configurations are running single instances
   - No horizontal scaling capabilities utilized
   - Limited failover and high availability

2. **Resource Utilization**
   - Base configurations show high resource utilization
   - Scaled configuration demonstrates better resource distribution

### Recommendations

1. **Infrastructure Optimization**
   - Consider implementing auto-scaling for Vector API and LLM components
   - Evaluate PostgreSQL connection pooling
   - Implement caching layer for frequently accessed vectors

2. **Cost Optimization**

```mermaid
   graph TB
       subgraph Recommended Setup
           A[Load Balancer] --> B1[Vector API Instance 1]
           A --> B2[Vector API Instance 2]
           B1 --> C[PGVector - Managed PostgreSQL]
           B2 --> C
           D[Cache Layer] --> C
       end
```

3. **Performance Tuning**
   - Implement query result caching
   - Optimize vector indexing strategies
   - Configure connection pooling
   - Fine-tune PostgreSQL parameters for vector operations

### Scaling Strategy

```mermaid
flowchart TD
    A[Monitor Load] --> B{High Load?}
    B -->|Yes| C[Scale Out Vector API]
    B -->|No| D[Maintain Current]
    C --> E{Response Time > 10s?}
    E -->|Yes| F[Scale Up DB]
    E -->|No| G[Monitor]
    F --> H[Evaluate Cost Impact]
```

## Conclusions

1. **Current Deployed Setup**
   - Running on base PGVector configuration
   - Single instances of all components
   - Average response time: ~25s (with cold starts up to 40s)
   - Base tier services

2. **Tested Scaling Benefits**
   - ~3.5x performance improvement
   - Improved reliability and consistency
   - Positive cost-performance ratio
   - Enhanced concurrent user support
   - Shows significant potential for high-traffic scenarios

3. **Scaling Recommendations**
   - Consider gradual scaling based on traffic
   - Start with Vector API scaling (most impact)
   - Monitor query patterns to optimize scaling decisions
   - Implement horizontal scaling before vertical scaling where possible

4. **Future Optimization Opportunities**
   - Implement caching layer to reduce database load
   - Add connection pooling
   - Consider hybrid scaling approach
   - Regular performance monitoring and cost analysis
