import asyncio
from backend.app.core.config import get_settings
from backend.app.database.database import create_db_engine, create_session_factory
from backend.app.database.models import Person, Conversation
from backend.app.services.import_service import ImportService
from backend.app.main import create_app

async def test_import():
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    
    app = create_app()
    vector_store = app.state.vector_store
    
    import_service = ImportService(vector_store=vector_store)
    
    with session_factory() as session:
        # Create person
        person = Person(name="Test User", description="For testing")
        session.add(person)
        session.commit()
        
        with open("backend/tests/data/whatsapp/chat.txt", "r", encoding="utf-8-sig") as f:
            file_content = f.read()
        
        # Import
        await import_service.import_whatsapp(
            session=session,
            person_id=person.id,
            filename="chat.txt",
            text=file_content
        )
        
        session.commit()
        print(f"Imported for person_id={person.id}")

if __name__ == "__main__":
    asyncio.run(test_import())
