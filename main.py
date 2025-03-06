from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
import uuid

# Modelo para los productos


class Product(BaseModel):
    # id: str = str(uuid.uuid4())
    name: str
    price: float
    quantity: int

# Modelo para el cliente


class Client(BaseModel):
    # id: str = str(uuid.uuid4())
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
    iva_rate: float  # Porcentaje de IVA
    total: float = 0  # Total calculado
    remaining_balance: float = 0  # Balance restante (inicializado en 0)
    status: InvoiceStatus = InvoiceStatus.pending  # Estado de la factura

    def update_balance(self, payment):
        self.remaining_balance -= payment.amount_paid
        # Redondear el saldo restante a 2 decimales
        self.remaining_balance = round(self.remaining_balance, 2)
        if self.remaining_balance <= 0:
            self.status = InvoiceStatus.paid
            self.remaining_balance = 0  # Asegurarse de que sea exactamente 0


# Métodos de pago posibles


class PaymentMethod(str, Enum):
    cash = "efectivo"
    card = "tarjeta"

# Modelo para el pago


class Payment(BaseModel):
    method: PaymentMethod  # Forma de pago (efectivo o tarjeta)
    amount_paid: float  # Monto que se paga


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Origen de tu aplicación React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulación de base de datos
invoices_db = {}

# Calcula el total con IVA


def calculate_total(products: List[Product], iva_rate: float) -> float:
    subtotal = sum(product.price * product.quantity for product in products)
    total = subtotal * (1 + iva_rate / 100)  # Sumar IVA
    return total

# Crear factura


@app.post("/create_invoice/")
async def create_invoice(invoice: Invoice):
    total = calculate_total(invoice.products, invoice.iva_rate)
    invoice.total = total
    invoice.remaining_balance = total  # Iniciar el balance restante con el total
    invoices_db[invoice.id] = invoice  # Guardar la factura en el diccionario
    return {"message": "Factura creada", "invoice_id": invoice.id, "invoice": invoice}

# Realizar pago


@app.post("/pay_invoice/{invoice_id}")
async def pay_invoice(invoice_id: str, payment: Payment):
    # Simulamos la búsqueda de la factura
    invoice = invoices_db.get(invoice_id)
    if not invoice:
        return {"error": "Factura no encontrada"}

    # Verificamos si el monto pagado no excede el saldo
    if payment.amount_paid > invoice.remaining_balance:
        return {"error": "El monto pagado excede el saldo de la factura"}

    # Actualizamos el balance de la factura
    invoice.update_balance(payment)

    # Retornamos la factura con el nuevo estado
    if invoice.remaining_balance == 0:
        return {"message": "Factura pagada exitosamente", "invoice": invoice}
    else:
        return {"message": "Pago realizado parcialmente", "invoice": invoice}


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
