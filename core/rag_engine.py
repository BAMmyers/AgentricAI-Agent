"""
RAG (Retrieval Augmented Generation) engine for document-aware AI responses.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
import PyPDF2

try:
    from langchain.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    DirectoryLoader = None
    TextLoader = None
    PyPDFLoader = None
    RecursiveCharacterTextSplitter = None

from core.config import get_config
from core.semantic_search import semantic_search


class RAGEngine:
    """Retrieval Augmented Generation engine."""
    
    def __init__(self, document_dir: Optional[str] = None):
        """Initialize RAG engine."""
        cfg = get_config()
        self.document_dir = Path(document_dir or cfg.get("documents_dir", Path.cwd() / "documents"))
        self.document_dir.mkdir(exist_ok=True)
        
        self.documents: List[Dict[str, Any]] = []
        self.chunk_size = 500
        self.chunk_overlap = 50
    
    async def index_documents(self, document_path: Optional[str] = None) -> int:
        """Index documents from a directory."""
        if document_path:
            path = Path(document_path)
        else:
            path = self.document_dir
        
        if not path.exists():
            return 0
        
        doc_count = 0
        
        # Process PDF files
        for pdf_file in path.glob("**/*.pdf"):
            try:
                doc_count += await self._process_pdf(pdf_file)
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
        
        # Process text files
        for text_file in path.glob("**/*.txt"):
            try:
                doc_count += await self._process_text_file(text_file)
            except Exception as e:
                print(f"Error processing {text_file}: {e}")
        
        # Process markdown files
        for md_file in path.glob("**/*.md"):
            try:
                doc_count += await self._process_text_file(md_file)
            except Exception as e:
                print(f"Error processing {md_file}: {e}")
        
        return doc_count
    
    async def _process_pdf(self, pdf_path: Path) -> int:
        """Process a PDF file and extract text."""
        count = 0
        
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    
                    # Split into chunks
                    chunks = self._chunk_text(text)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        self.documents.append({
                            "source": str(pdf_path),
                            "page": page_num + 1,
                            "chunk": chunk_idx,
                            "content": chunk,
                            "doc_type": "pdf"
                        })
                        count += 1
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
        
        return count
    
    async def _process_text_file(self, file_path: Path) -> int:
        """Process a text file."""
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = self._chunk_text(text)
            
            for chunk_idx, chunk in enumerate(chunks):
                self.documents.append({
                    "source": str(file_path),
                    "chunk": chunk_idx,
                    "content": chunk,
                    "doc_type": "text"
                })
                count += 1
        except Exception as e:
            print(f"Error processing text file {file_path}: {e}")
        
        return count
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    async def retrieve_relevant_documents(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve documents relevant to a query."""
        if not self.documents:
            return []
        
        # Search for relevant documents using semantic search
        results = await semantic_search.semantic_search(query, top_k=top_k)
        
        # Enhance with full document info
        enhanced_results = []
        for result in results:
            # Find matching document
            for doc in self.documents:
                if doc["content"] in result.get("content", ""):
                    enhanced_results.append({
                        "source": doc["source"],
                        "content": doc["content"],
                        "doc_type": doc.get("doc_type"),
                        "relevance": 1.0 - (result.get("distance", 0) / 1000)  # Normalize distance
                    })
                    break
        
        return enhanced_results[:top_k]
    
    async def augment_prompt(
        self,
        original_prompt: str,
        retrieved_docs: Optional[List[Dict[str, Any]]] = None,
        context_query: Optional[str] = None
    ) -> str:
        """Augment a prompt with retrieved document context."""
        if not retrieved_docs and not context_query:
            return original_prompt
        
        if context_query and not retrieved_docs:
            retrieved_docs = await self.retrieve_relevant_documents(context_query)
        
        if not retrieved_docs:
            return original_prompt
        
        # Build augmented prompt
        augmented = f"""You are an AI assistant with access to the following documents:

--- RETRIEVED DOCUMENTS ---
"""
        
        for i, doc in enumerate(retrieved_docs, 1):
            augmented += f"\n[Document {i} - {doc.get('source', 'Unknown')}]\n"
            augmented += f"{doc['content'][:500]}...\n"
        
        augmented += f"""--- END DOCUMENTS ---

Use the information from these documents to inform your response when relevant.

Original Query: {original_prompt}

Response:
"""
        
        return augmented


# Global RAG engine instance
rag_engine = RAGEngine()
