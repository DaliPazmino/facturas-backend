from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
import uuid

# Modelo para los productos
class Product(BaseModel):
    name: str
    price: float
    quantity: int

# Modelo para el cliente
class Client(BaseModel):
    name: str
    cedula: str
    email: str
    address: str

# Estados posibles de la factura
class InvoiceStatus(str, Enum):
    pending = "pendiente"
    paid = "pagada"

# Modelo para la factura
class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client: Client
    products: List[Product]
    iva_rate: float
    total: float = 0
    remaining_balance: float = 0
    status: InvoiceStatus = InvoiceStatus.pending

    def update_balance(self, payment):
        self.remaining_balance -= payment.amount_paid
        self.remaining_balance = round(self.remaining_balance, 2)
        if self.remaining_balance <= 0:
            self.status = InvoiceStatus.paid
            self.remaining_balance = 0

# Métodos de pago
class PaymentMethod(str, Enum):
    cash = "efectivo"
    card = "tarjeta"

# Modelo para el pago
class Payment(BaseModel):
    method: PaymentMethod
    amount_paid: float

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://facturas-frontend.onrender.com",  # Reemplaza con tu URL de frontend en Render
        "http://localhost:5173"  # Solo para desarrollo local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de datos simulada
invoices_db = {}

# Calcula el total con IVA
def calculate_total(products: List[Product], iva_rate: float) -> float:
    subtotal = sum(product.price * product.quantity for product in products)
    total = subtotal * (1 + iva_rate / 100)
    return total

# Endpoint raíz para comprobar que el backend está funcionando
@app.get("/")
def read_root():
    return {"message": "API de facturación funcionando correctamente 🚀"}

# Crear factura
@app.post("/create_invoice/")
async def create_invoice(invoice: Invoice):
    total = calculate_total(invoice.products, invoice.iva_rate)
    invoice.total = total
    invoice.remaining_balance = total
    invoices_db[invoice.id] = invoice
    return {"message": "Factura creada correctamente", "invoice_id": invoice.id, "invoice": invoice}

# Realizar pago
@app.post("/pay_invoice/{invoice_id}")
async def pay_invoice(invoice_id: str, payment: Payment):
    invoice = invoices_db.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if payment.amount_paid > invoice.remaining_balance:
        raise HTTPException(status_code=400, detail="El monto pagado excede el saldo de la factura")

    invoice.update_balance(payment)

    message = "Pago realizado parcialmente"
    if invoice.remaining_balance == 0:
        message = "Factura pagada exitosamente"

    return {"message": message, "invoice": invoice}

# Obtener todas las facturas
@app.get("/invoices/", response_model=List[Invoice])
async def get_invoices():
    return list(invoices_db.values())

# Obtener una factura por ID
@app.get("/invoice/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    invoice = invoices_db.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice
