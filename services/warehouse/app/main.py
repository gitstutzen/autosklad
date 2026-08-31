from fastapi import FastAPI
from app.routers import positions, tasks

app = FastAPI(
    title="warehouse",
    description="Приёмка товара: задания, позиции, статусы. "
                 "Портирует бизнес-логику FormStock.SavePosition/FormStockInputMark.",
)

app.include_router(tasks.router, prefix="/warehouse/tasks", tags=["tasks"])
app.include_router(positions.router, prefix="/warehouse/positions", tags=["positions"])


@app.get("/health")
def health():
    return {"status": "ok"}
