import os
import cyborgdb_lite as cyborgdb
import secrets
from typing import List, Dict, Any
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class CyborgDBRAG:
    """
    CyborgDB integration for Retrieval-Augmented Generation (RAG) in medical context.
    Provides secure, encrypted vector search for medical knowledge retrieval.
    """

    def __init__(self):
        """Initialize CyborgDB client and medical knowledge index"""
        # Get API key from environment
        self.api_key = os.getenv("CYBORGDB_API_KEY")
        if not self.api_key:
            raise ValueError("CYBORGDB_API_KEY not found in environment variables")

        # Configure Gemini for embeddings
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = genai.GenerativeModel('gemini-2.5-pro')

        # Configure CyborgDB with in-memory storage 
        index_location = cyborgdb.DBConfig("memory")
        config_location = cyborgdb.DBConfig("memory")
        items_location = cyborgdb.DBConfig("memory")

        # Create CyborgDB client
        self.client = cyborgdb.Client(
            self.api_key,
            index_location,
            config_location,
            items_location
        )

        # Generate or load encryption key
        self.index_key = self._get_or_create_encryption_key()

        # Initialize medical knowledge index
        self.index = None
        self._initialize_medical_index()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get existing encryption key or create a new one"""
        key_file = ".cyborgdb_key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = secrets.token_bytes(32)
            with open(key_file, "wb") as f:
                f.write(key)
            return key

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector from text using Gemini.
        For this implementation, we'll use a simple approach to convert text to vector.
        In production, use proper embedding models.
        """
        # Use Gemini to generate a meaningful embedding representation
        # For hackathon demo, we'll create a simple hash-based embedding
        # In production, use proper embedding models like text-embedding-004

        # Simple approach: hash the text and create a fixed-size vector
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to 768-dimensional vector (common embedding size)
        vector = []
        for i in range(768):
            vector.append(float(hash_bytes[i % len(hash_bytes)]) / 255.0)

        return vector

    def _initialize_medical_index(self):
        """Initialize the medical knowledge index with sample data"""
        try:
            # Try to get existing index
            self.index = self.client.get_index("medical_knowledge")
            print("Loaded existing medical knowledge index")
        except:
            # Create new index if it doesn't exist
            print("Creating new medical knowledge index...")

            # Define index configuration (768 dimensions for text embeddings)
            index_config = cyborgdb.IndexIVFFlat(dimension=768)

            # Create encrypted index
            self.index = self.client.create_index(
                "medical_knowledge",
                self.index_key,
                index_config
            )

            # Populate with initial medical knowledge
            self._populate_medical_knowledge()
            print("Created and populated medical knowledge index")

    def _populate_medical_knowledge(self):
        """Populate the index with medical knowledge base"""
        medical_knowledge = [
            {
                "id": "emergency_chest_pain",
                "contents": "Chest pain with radiation to arm or jaw, accompanied by sweating, indicates potential heart attack. This is a medical emergency requiring immediate hospitalization. Symptoms include pressure, tightness, or crushing sensation in the chest.",
                "category": "emergency",
                "specialty": "cardiology"
            },
            {
                "id": "emergency_stroke",
                "contents": "Sudden weakness on one side of body, face drooping, slurred speech, or sudden confusion are signs of stroke. Time is critical - immediate emergency care needed. Remember FAST: Face drooping, Arm weakness, Speech difficulty, Time to call emergency.",
                "category": "emergency",
                "specialty": "neurology"
            },
            {
                "id": "emergency_breathing",
                "contents": "Severe difficulty breathing, turning blue, or choking requires immediate emergency care. Cannot speak in full sentences, gasping for air, or severe shortness of breath are critical signs.",
                "category": "emergency",
                "specialty": "pulmonology"
            },
            {
                "id": "non_emergency_headache",
                "contents": "Headaches including tension headaches and migraines typically do not require emergency care unless accompanied by stroke symptoms. Can be managed by primary care physician or neurologist. Common causes include stress, dehydration, or tension.",
                "category": "non_emergency",
                "specialty": "neurology"
            },
            {
                "id": "non_emergency_fever",
                "contents": "Fever in adults without other severe symptoms can typically wait for doctor appointment. Exception: infants under 3 months with fever need immediate evaluation. Seek care if fever persists beyond 3 days or exceeds 103°F.",
                "category": "non_emergency",
                "specialty": "general_medicine"
            },
            {
                "id": "non_emergency_skin_rash",
                "contents": "Skin rashes, acne, eczema, or dermatitis are typically non-emergency conditions. Can be evaluated by dermatologist or primary care physician. Exception: rash with fever, difficulty breathing, or swelling of face/throat needs immediate care.",
                "category": "non_emergency",
                "specialty": "dermatology"
            },
            {
                "id": "non_emergency_joint_pain",
                "contents": "Joint pain, arthritis, back pain, or muscle aches are typically non-emergency. Can be evaluated by orthopedic specialist or primary care. Urgent care if severe trauma, inability to move limb, or severe swelling.",
                "category": "non_emergency",
                "specialty": "orthopedics"
            },
            {
                "id": "non_emergency_digestive",
                "contents": "Nausea, vomiting, diarrhea, or mild abdominal pain are typically non-emergency. Can be managed by gastroenterologist or primary care. Emergency if severe dehydration, blood in vomit/stool, or severe abdominal pain.",
                "category": "non_emergency",
                "specialty": "gastroenterology"
            },
            {
                "id": "emergency_anaphylaxis",
                "contents": "Anaphylaxis is a severe allergic reaction causing throat swelling, difficulty breathing, widespread hives, or rapid pulse. This is a life-threatening emergency requiring immediate epinephrine and emergency care.",
                "category": "emergency",
                "specialty": "allergy_immunology"
            },
            {
                "id": "emergency_severe_bleeding",
                "contents": "Uncontrollable bleeding, spurting blood, or deep wounds require immediate emergency care. Apply direct pressure and call emergency services. Large blood loss can be life-threatening within minutes.",
                "category": "emergency",
                "specialty": "trauma_surgery"
            }
        ]

        # Generate embeddings and prepare items for insertion
        items = []
        for knowledge in medical_knowledge:
            vector = self._generate_embedding(knowledge["contents"])
            items.append({
                "id": knowledge["id"],
                "vector": vector,
                "contents": json.dumps(knowledge)
            })

        # Upsert items into the index
        self.index.upsert(items)
        print(f"Inserted {len(items)} medical knowledge items")

    def query_medical_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Query the medical knowledge base using RAG

        Args:
            query: The medical query/symptoms
            top_k: Number of top results to return

        Returns:
            List of relevant medical knowledge items
        """
        # Generate embedding for the query
        query_vector = self._generate_embedding(query)

        # Query the encrypted index
        results = self.index.query(query_vector, top_k=top_k)

        # Parse and return results
        knowledge_items = []
        for result in results:
            try:
                content_dict = json.loads(result.contents)
                knowledge_items.append({
                    "id": result.id,
                    "distance": result.distance,
                    "contents": content_dict.get("contents", ""),
                    "category": content_dict.get("category", ""),
                    "specialty": content_dict.get("specialty", "")
                })
            except json.JSONDecodeError:
                continue

        return knowledge_items

    def add_medical_knowledge(self, knowledge_id: str, contents: str,
                             category: str, specialty: str):
        """
        Add new medical knowledge to the index

        Args:
            knowledge_id: Unique identifier for the knowledge item
            contents: Medical knowledge content
            category: Category (emergency/non_emergency)
            specialty: Medical specialty
        """
        knowledge = {
            "id": knowledge_id,
            "contents": contents,
            "category": category,
            "specialty": specialty
        }

        vector = self._generate_embedding(contents)
        item = {
            "id": knowledge_id,
            "vector": vector,
            "contents": json.dumps(knowledge)
        }

        self.index.upsert([item])
        print(f"Added medical knowledge: {knowledge_id}")

    def get_rag_context(self, query: str) -> str:
        """
        Get RAG context for a medical query

        Args:
            query: The medical query

        Returns:
            Formatted context string from RAG retrieval
        """
        results = self.query_medical_knowledge(query, top_k=3)

        if not results:
            return "No relevant medical knowledge found."

        context = "Relevant Medical Knowledge:\n\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. [{result['category'].upper()}] ({result['specialty']})\n"
            context += f"   {result['contents']}\n\n"

        return context


# Test the implementation
if __name__ == "__main__":
    print("Initializing CyborgDB RAG system...")
    rag = CyborgDBRAG()

    # Test queries
    test_queries = [
        "I have severe chest pain radiating to my left arm",
        "I have a headache that won't go away",
        "I have a skin rash on my arms"
    ]

    print("\n" + "="*60)
    print("Testing Medical Knowledge Retrieval")
    print("="*60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        context = rag.get_rag_context(query)
        print(context)
