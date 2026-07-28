import json
import re
from typing import Any, Dict, Generator, List, Optional

from src.core.llm_provider import LLMProvider
from src.tools.tools import CATALOG, SHIPPING_ZONES


class DemoProvider(LLMProvider):
    """Deterministic local provider for the browser demo."""

    def __init__(self, mode: str):
        if mode not in {"chatbot", "agent"}:
            raise ValueError("mode must be 'chatbot' or 'agent'")
        super().__init__(model_name=f"demo-{mode}")
        self.mode = mode
        self.calls = 0

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        self.calls += 1
        content = (
            self._chatbot_response(prompt)
            if self.mode == "chatbot"
            else self._agent_response(prompt)
        )
        return {
            "content": content,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split()),
            },
            "latency_ms": 0,
            "provider": "demo",
        }

    def stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]

    def _chatbot_response(self, prompt: str) -> str:
        query = prompt.casefold()
        if "return policy" in query or "đổi trả" in query:
            return (
                "Sản phẩm chưa qua sử dụng có thể được đổi trả trong 30 ngày "
                "khi có bằng chứng mua hàng."
            )
        if "working hours" in query or "giờ làm việc" in query:
            return "Bộ phận hỗ trợ làm việc từ thứ Hai đến thứ Sáu, 09:00–17:00."
        return (
            "Tôi là chatbot baseline nên không thể xác minh giá, tồn kho, "
            "coupon hoặc phí vận chuyển hiện tại. Hãy chuyển sang Agent để "
            "lấy dữ liệu từ tool."
        )

    def _agent_response(self, prompt: str) -> str:
        query = self._question(prompt)
        lowered = query.casefold()
        observations = self._observations(prompt)

        if "return policy" in lowered or "đổi trả" in lowered:
            return (
                "Final Answer: Sản phẩm chưa qua sử dụng có thể được đổi trả "
                "trong 30 ngày khi có bằng chứng mua hàng."
            )
        if "working hours" in lowered or "giờ làm việc" in lowered:
            return (
                "Final Answer: Bộ phận hỗ trợ làm việc từ thứ Hai đến thứ Sáu, "
                "09:00–17:00."
            )

        product = self._product(query)
        stock = self._find_observation(observations, "stock")
        discount = self._find_observation(observations, "discount_percent")
        shipping = self._find_observation(observations, "shipping_cost")

        if product and stock is None:
            return (
                "Thought: Cần kiểm tra giá và tồn kho.\n"
                f'Action: check_stock({{"item_name": "{product}"}})'
            )

        if stock and stock.get("status") == "out_of_stock":
            return (
                f"Final Answer: {stock['item_name']} hiện đã hết hàng. "
                "Tôi dừng tại đây và không khẳng định có thể mua."
            )

        coupon = self._coupon(query)
        if coupon and discount is None:
            return (
                "Thought: Cần xác minh mã giảm giá.\n"
                f'Action: get_discount({{"coupon_code": "{coupon}"}})'
            )

        destination = self._destination(query)
        if destination and shipping is None:
            weight = self._weight(query)
            quantity = self._quantity(query)
            if weight is None and stock:
                weight = float(stock["weight_kg"]) * quantity
            if weight is not None:
                return (
                    "Thought: Cần tính phí giao hàng.\n"
                    "Action: calc_shipping("
                    f'{{"weight": {weight}, "destination": "{destination}"}})'
                )

        if stock:
            quantity = self._quantity(query)
            subtotal = int(stock["price"]) * quantity
            discount_percent = (
                int(discount["discount_percent"])
                if discount and discount.get("valid")
                else 0
            )
            discounted = subtotal * (100 - discount_percent) // 100
            shipping_cost = int(shipping["shipping_cost"]) if shipping else 0
            total = discounted + shipping_cost
            coupon_note = (
                f" Coupon giảm {discount_percent}% đã được áp dụng."
                if discount_percent
                else (" Coupon không hợp lệ nên không giảm giá." if coupon else "")
            )
            shipping_note = (
                f" Phí vận chuyển là {shipping_cost:,} VND."
                if shipping
                else ""
            )
            return (
                f"Final Answer: Tổng tiền có căn cứ là {total:,} VND."
                f"{coupon_note}{shipping_note}"
            )

        return (
            "Final Answer: Tôi chưa có tool phù hợp để xác minh yêu cầu này, "
            "nên không đưa ra thông tin chưa có căn cứ."
        )

    @staticmethod
    def _question(prompt: str) -> str:
        match = re.search(r"^Question:\s*(.+?)(?:\n\n|\Z)", prompt, re.DOTALL)
        return match.group(1).strip() if match else prompt.strip()

    @staticmethod
    def _observations(prompt: str) -> List[Dict[str, Any]]:
        results = []
        for line in prompt.splitlines():
            if not line.startswith("Observation: "):
                continue
            try:
                value = json.loads(line.removeprefix("Observation: "))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                results.append(value)
        return results

    @staticmethod
    def _find_observation(
        observations: List[Dict[str, Any]], key: str
    ) -> Optional[Dict[str, Any]]:
        return next((item for item in observations if key in item), None)

    @staticmethod
    def _product(query: str) -> Optional[str]:
        lowered = query.casefold()
        products = sorted(
            (item["item_name"] for item in CATALOG.values()),
            key=len,
            reverse=True,
        )
        for product in products:
            if product.casefold() in lowered:
                return product
        return None

    @staticmethod
    def _coupon(query: str) -> Optional[str]:
        match = re.search(
            r"(?:code|mã)\s*['\"]?([A-Za-z0-9_-]+)", query, re.IGNORECASE
        )
        return match.group(1).upper() if match else None

    @staticmethod
    def _destination(query: str) -> Optional[str]:
        lowered = query.casefold()
        aliases = sorted(SHIPPING_ZONES, key=len, reverse=True)
        for alias in aliases:
            if alias in lowered:
                return SHIPPING_ZONES[alias]["destination"]
        return None

    @staticmethod
    def _weight(query: str) -> Optional[float]:
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", query, re.IGNORECASE)
        return float(match.group(1).replace(",", ".")) if match else None

    @staticmethod
    def _quantity(query: str) -> int:
        match = re.search(
            r"(?:buy|mua|lấy)\s+(\d+)|(\d+)\s*(?:iphone|ipad|macbook)",
            query,
            re.IGNORECASE,
        )
        if not match:
            return 1
        return int(match.group(1) or match.group(2))
