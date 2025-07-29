### Our Approach: From Structure to Persona-Driven Insight

Our solution, the Persona-Intel Engine, is designed to transform a static collection of documents into a dynamic source of targeted intelligence. The core philosophy is that true relevance comes from understanding not just *what* a user is asking, but *who* is asking it. Our methodology is a three-stage pipeline built for accuracy, speed, and offline functionality.

**Stage 1: Semantic Foundation via Structural Linking**

Our process begins by "connecting the dots" back to Round 1A. We ingest the hierarchically structured JSON output from our previous work, which provides a logical map of each document's sections. Instead of using naive, fixed-size text splitting—a method that often severs context mid-sentence—we perform **Semantic Chunking**. Each heading identified in the document outline is treated as a distinct, self-contained semantic concept. This ensures that every piece of text we analyze is a logical unit (e.g., "Coastal Adventures," "General Packing Tips"), dramatically improving the quality of our downstream analysis.

**Stage 2: Persona-Aware Querying and Embedding**

To fully capture user intent, we formulate a **compound query** by combining the user's `Persona` with their `Job-to-be-Done`. This enriched query provides our embedding model with crucial context about the *lens* through which the information should be viewed. We use the `all-MiniLM-L6-v2` sentence-transformer model, specifically chosen for its excellent performance-to-size ratio and its efficiency on CPU. This model converts our compound query and all semantic chunks into high-dimensional vectors. The entire model is pre-packaged within our Docker container during the build process, guaranteeing full compliance with the strict offline and size constraints.

**Stage 3: High-Speed Retrieval and Ranking**

Finally, we employ a high-speed retrieval system to deliver the ranked results. We calculate the **cosine similarity** between the compound query vector and every semantic chunk vector. This gives us a precise numerical score for the relevance of each section to the user's specific need. The sections are then ranked in descending order of this score. The top-ranked sections are presented in the `extracted_sections` output. For the `subsection_analysis`, we provide the core text of these top sections, offering a transparent view into what made them relevant. This entire pipeline provides a fast, accurate, and context-aware solution to the document intelligence challenge.