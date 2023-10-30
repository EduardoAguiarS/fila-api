import datetime
from sqlmodel import SQLModel, Field, create_engine, Session
from fastapi.security.api_key import APIKeyHeader
from fastapi import FastAPI, status, Security, HTTPException

API_KEY = "123asd"
API_KEY_NAME = "Authorization"
api_key_header_auth = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


def get_api_key(api_key_header: str = Security(api_key_header_auth)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


app = FastAPI()


class Fila(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, nullable=False)
    nome: str = Field(default=None, max_length=20, nullable=False)
    tipo: str = Field(default=None, max_length=1, nullable=False)
    atendido: bool = Field(default=False, nullable=False)
    data: str = Field(default=None, max_length=30, nullable=False)
    pos: int = Field(default=None, nullable=False)


SQLITE_FILE_NAME = "database.db"
sqlite_url = f"sqlite:///{SQLITE_FILE_NAME}"
engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_db_and_tables()

session = Session(engine)


@app.get("/", status_code=status.HTTP_200_OK)
async def home():
    return {
        "message": "API de Fila",
    }


@app.get("/fila/", dependencies=[Security(get_api_key)], status_code=status.HTTP_200_OK)
async def read_fila():
    if len(session.query(Fila).all()) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não há pessoas na fila",
        )
    return session.query(Fila).filter(Fila.atendido == False).all()


@app.get("/fila/{id}", dependencies=[Security(get_api_key)], status_code=status.HTTP_200_OK)
async def read_fila_id(id: int):
    if session.query(Fila).filter(Fila.id == id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pessoa não existe",
        )
    return session.query(Fila).filter(Fila.id == id).first()


@app.post("/fila/", dependencies=[Security(get_api_key)], status_code=status.HTTP_201_CREATED)
async def create_fila(fila: Fila):
    total = session.query(Fila).filter(Fila.atendido == False).all()
    if fila.id in [fila.id for fila in total]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pessoa já está na fila",
        )
    if len(total) == 0:
        fila.id = 1
    else:
        fila.id = max([fila.id for fila in total]) + 1

    if fila.tipo == "P" or fila.tipo == "p" or fila.tipo == "N" or fila.tipo == "n":
        fila.data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        fila.atendido = False
        if fila.tipo == "P" or fila.tipo == "p":
            fila.pos = len(
                [fila for fila in total if fila.tipo == "P" or fila.tipo == "p"]) + 1
        else:
            fila.pos = len(
                [fila for fila in total if fila.tipo == "N" or fila.tipo == "n"]) + 1
        session.add(fila)
        session.commit()
        session.refresh(fila)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de pessoa inválido, escolha P ou N, P para preferencial e N para normal",
        )
    return {
        "message": "Pessoa adicionada na fila",
        "data": fila,
    }


@app.put("/fila/{tipe}", dependencies=[Security(get_api_key)], status_code=status.HTTP_200_OK)
async def update_fila(tipe: str):
    fila = session.query(Fila).filter(Fila.tipo == tipe).all()

    if len(fila) == 0 or tipe != "P" and tipe != "p" and tipe != "N" and tipe != "n":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não há pessoas na fila ou tipo inválido, escolha P ou N, P para preferencial e N para normal",
        )
    for i in range(len(fila)):
        if fila[i].atendido == False:
            fila[i].pos = fila[i].pos - 1
            if fila[i].pos == 0:
                fila[i].atendido = True
    session.commit()
    return {
        "message": "Fila atualizada",
    }


@app.delete("/fila/{id}", dependencies=[Security(get_api_key)], status_code=status.HTTP_200_OK)
async def delete_fila(id: int):
    person = session.query(Fila).filter(Fila.id == id).first()
    if person is None or person.atendido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pessoa não existe, ou já foi atendida",
        )

    session.delete(person)
    session.commit()

    fila = session.query(Fila).filter(Fila.tipo == person.tipo).all()
    if len(fila) == 0:
        return {
            "message": "Pessoa removida da fila",
        }
    for i in range(len(fila)):
        if fila[i].atendido == False:
            fila[i].pos = fila[i].pos - 1
            if fila[i].pos == 0:
                fila[i].atendido = True
    session.commit()
    return {
        "message": "Pessoa removida da fila",
    }
