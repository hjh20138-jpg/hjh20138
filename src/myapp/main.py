from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from myapp.inquiries import router as inquiries_router
from myapp.reservations import router as reservations_router

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.abeliophyllum.art",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(inquiries_router)
app.include_router(reservations_router)

ITEMS = {
    1: {"id": 1, "name": "apple", "price": 3000},
    2: {"id": 2, "name": "banana", "price": 1500},
    3: {"id": 3, "name": "orange", "price": 2000},
}


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    price: int = Field(ge=0)


@app.get("/")
def root():
    return {"hello": "world"}


@app.get("/apple")
def apple():
    return {"apple": "expensive"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items(max_price: int | None = None):
    items = list(ITEMS.values())
    if max_price is not None:
        items = [item for item in items if item["price"] <= max_price]
    return {"items": items}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@app.post("/items", status_code=201)
def create_item(body: ItemCreate):
    item_id = max(ITEMS) + 1
    item = {"id": item_id, "name": body.name, "price": body.price}
    ITEMS[item_id] = item
    return item