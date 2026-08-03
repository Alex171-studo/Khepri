from pydantic import BaseModel, Field
from typing import  Literal
from enum import Enum

class CheckoutErrorCode(str, Enum):
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PAYMENT_PROVIDER_DOWN = "PAYMENT_PROVIDER_DOWN"
    INVALID_ADDRESS = "INVALID_ADDRESS"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    EMPTY_CART = "EMPTY_CART"

class purchase_item(BaseModel):
    product_id: str = Field(description="The ID of the product being purchased")
    quantity: int = Field(gt=0, description="The quantity of the product being purchased")

class CheckoutRequest(BaseModel):
    customer_name: str = Field(description="The name of the customer making the purchase")
    customer_phone: str = Field(description="The phone number of the customer")
    delivery_address: str = Field(description="The delivery address for the order")
    items: list[purchase_item] = Field(description="A list of items being purchased")

class CheckoutResponse(BaseModel):
    order_id: str = Field(description="The ID of the created order")
    payment_url: str = Field(description="The URL to complete the payment")
    status: Literal["pending","paid", "cancelled"] = Field(default="pending", description="The status of the checkout process")
    expires_at: str = Field(description="The expiration time of the checkout session in ISO 8601 format")
    total_amount: float = Field(gt=0, description="The total amount to be paid for the order")
    currency: str = Field(default="XOF", description="The currency of the total amount, e.g., USD, EUR")
    success: bool = Field(default=True, description="Indicates whether the checkout process was successful")

class CheckoutErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Indicates whether the checkout process was successful")
    error_code: CheckoutErrorCode = Field(description="The specific error code indicating the reason for the failure")
    reason: str = Field(description="A human-readable explanation of the error")
