# Bedrock Titan Embeddings Migration

## What Changed
- Replaced sentence-transformers (768D) with AWS Bedrock Titan Embeddings (1024D)
- Removed 420MB model download from Docker build
- Using cloud-based embeddings via AWS API
- Faster Docker builds and smaller container size

## To Complete Migration

1. **Start Docker and rebuild containers:**
```bash
make build
make up
```

2. **Run the migration script:**
```bash
docker-compose exec backend python migrate_to_titan.py
```

This will:
- Drop old 768D embeddings column
- Create new 1024D column for Titan v2
- Re-embed all documents using Bedrock Titan
- Verify embeddings are working

3. **Test the new embeddings:**
```bash
docker-compose exec backend python test_titan_embedding.py
```

4. **Test vector search:**
```bash
curl http://localhost:3030/api/test/test-refund-search
```

## Benefits
- ✅ No more model downloads (420MB saved)
- ✅ Faster Docker builds
- ✅ Consistent with Bedrock usage (Nova for analysis, Titan for embeddings)
- ✅ Better scalability (API-based vs local model)
- ✅ Higher quality embeddings from AWS Titan

## Troubleshooting
- Ensure AWS credentials are configured
- Verify Bedrock is enabled in us-east-1 region
- Check you have access to Titan Embed models