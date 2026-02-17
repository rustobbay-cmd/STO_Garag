import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///./sto_base.db")
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    client_name = Column(String)
    client_phone = Column(String)
    service_name = Column(String)  # "Развал" или "Ходовая"
    start_time = Column(DateTime)
    duration = Column(Float)       # в часах

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all())

async def add_appointment(name, phone, service, start_dt, duration):
    async with async_session() as session:
        new_app = Appointment(
            client_name=name,
            client_phone=phone,
            service_name=service,
            start_time=start_dt,
            duration=duration
        )
        session.add(new_app)
        await session.commit()

async def get_today_appointments():
    async with async_session() as session:
        result = await session.execute(select(Appointment).order_by(Appointment.start_time))
        return result.scalars().all()

