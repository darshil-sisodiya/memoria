"""Initial model tests."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.database import Base
from backend.app.database.models import Conversation, ConversationMessage, Memory, Message, Person, Photo


def test_initial_entities_can_be_persisted() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        person = Person(name="Synthetic Person", description="Synthetic test data")
        person.messages.append(Message(sender="Synthetic Person", content="Hello", source="manual"))
        person.memories.append(Memory(title="Test memory", content="A synthetic memory", importance=1))
        conversation = Conversation(title="Test conversation")
        conversation.messages.append(ConversationMessage(role="user", content="Hi"))
        person.conversations.append(conversation)
        person.photos.append(Photo(file_path="data/example.jpg", filename="example.jpg"))
        session.add(person)
        session.commit()

        saved_person = session.get(Person, person.id)
        assert saved_person is not None
        assert len(saved_person.messages) == 1
        assert len(saved_person.memories) == 1
        assert len(saved_person.conversations[0].messages) == 1
        assert len(saved_person.photos) == 1

    engine.dispose()

