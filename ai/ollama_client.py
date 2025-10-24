"""
Ollama client for local AI interactions
"""
import json
import requests
from typing import Dict, Any, Optional, List
from config import OLLAMA_HOST, OLLAMA_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS


class OllamaClient:
    """
    Client for interacting with Ollama local AI.
    """

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        """
        Initialize Ollama client.

        Args:
            host: Ollama API host URL
            model: Model name to use
        """
        self.host = host.rstrip('/')
        self.model = model
        self.api_url = f"{self.host}/api"

    def generate(self, prompt: str, system: Optional[str] = None,
                temperature: float = AI_TEMPERATURE,
                max_tokens: int = AI_MAX_TOKENS) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: User prompt
            system: Optional system message
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            ConnectionError: If cannot connect to Ollama
            RuntimeError: If generation fails
        """
        url = f"{self.api_url}/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                f"Make sure Ollama is running (ollama serve)"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError("Ollama request timed out")
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    def chat(self, messages: List[Dict[str, str]],
            temperature: float = AI_TEMPERATURE,
            max_tokens: int = AI_MAX_TOKENS) -> str:
        """
        Chat with Ollama using message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response
        """
        url = f"{self.api_url}/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            message = result.get("message", {})
            return message.get("content", "")

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                f"Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama chat failed: {str(e)}")

    def is_available(self) -> bool:
        """
        Check if Ollama is available.

        Returns:
            True if Ollama is accessible
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """
        List available models.

        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])
            return [m.get("name") for m in models]

        except Exception:
            return []

    def analyze_statement(self, statement_data: Dict[str, Any],
                         query: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze bank statement data with a query.

        Args:
            statement_data: Parsed statement data
            query: User query/question
            system_prompt: Optional system prompt

        Returns:
            AI analysis response
        """
        # Prepare context from statement data
        summary = statement_data.get('summary', {})
        metadata = statement_data.get('metadata', {})
        balance = statement_data.get('balance', {})

        context = f"""
สรุปข้อมูลบัญชี:
- ธนาคาร: {metadata.get('bank', 'N/A')}
- ประเภทบัญชี: {metadata.get('account_type', 'N/A')}
- ระยะเวลา: {metadata.get('statement_period', {}).get('start_date', 'N/A')} ถึง {metadata.get('statement_period', {}).get('end_date', 'N/A')}

ยอดเงิน:
- ยอดเริ่มต้น: {balance.get('opening', 0):,.2f} บาท
- ยอดปิด: {balance.get('closing', 0):,.2f} บาท
- ยอดเฉลี่ย: {balance.get('average', 0):,.2f} บาท

สรุปรายการ:
- จำนวนรายการทั้งหมด: {summary.get('total_transactions', 0)}
- รายจ่ายรวม: {summary.get('total_debit', 0):,.2f} บาท
- รายรับรวม: {summary.get('total_credit', 0):,.2f} บาท
- เงินเปลี่ยนแปลง: {summary.get('net_change', 0):,.2f} บาท

รายจ่ายตามหมวด:
{json.dumps(summary.get('by_category', {}), ensure_ascii=False, indent=2)}

ช่องทางทำรายการ:
{json.dumps(summary.get('by_channel', {}), ensure_ascii=False, indent=2)}
"""

        # Default system prompt if not provided
        if not system_prompt:
            system_prompt = """คุณเป็นผู้ช่วยวิเคราะห์การเงินที่ชำนาญด้านธนาคารไทย
ให้คำตอบที่แม่นยำ กระชับ และเป็นประโยชน์ในการจัดการเงิน
ตอบเป็นภาษาไทยเสมอ ยกเว้นมีคำขอเป็นอย่างอื่น"""

        full_prompt = f"{context}\n\nคำถาม: {query}\n\nคำตอบ:"

        return self.generate(full_prompt, system=system_prompt)
