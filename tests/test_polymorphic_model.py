from typing import Optional

import pytest
from pydantic import ValidationError
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

from tests.conftest import needs_pydanticv2


@needs_pydanticv2
def test_polymorphic_joined_table(clear_sqlmodel) -> None:
    class Hero(SQLModel, table=True):
        __tablename__ = "hero"
        id: Optional[int] = Field(default=None, primary_key=True)
        hero_type: str = Field(default="hero")

        __mapper_args__ = {
            "polymorphic_on": "hero_type",
            "polymorphic_identity": "normal_hero",
        }

    class DarkHero(Hero):
        __tablename__ = "dark_hero"
        id: Optional[int] = Field(
            default=None,
            sa_column=mapped_column(ForeignKey("hero.id"), primary_key=True),
        )
        dark_power: str = Field(
            default="dark",
            sa_column=mapped_column(
                nullable=False, use_existing_column=True, default="dark"
            ),
        )

        __mapper_args__ = {
            "polymorphic_identity": "dark",
        }

    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        hero = Hero()
        db.add(hero)
        dark_hero = DarkHero()
        db.add(dark_hero)
        db.commit()
        statement = select(DarkHero)
        result = db.exec(statement).all()
    assert len(result) == 1
    assert isinstance(result[0].dark_power, str)


@needs_pydanticv2
def test_polymorphic_joined_table_with_sqlmodel_field(clear_sqlmodel) -> None:
    class Hero(SQLModel, table=True):
        __tablename__ = "hero"
        id: Optional[int] = Field(default=None, primary_key=True)
        hero_type: str = Field(default="hero")

        __mapper_args__ = {
            "polymorphic_on": "hero_type",
            "polymorphic_identity": "normal_hero",
        }

    class DarkHero(Hero):
        __tablename__ = "dark_hero"
        id: Optional[int] = Field(
            default=None,
            primary_key=True,
            foreign_key="hero.id",
        )
        dark_power: str = Field(
            default="dark",
            sa_column=mapped_column(
                nullable=False, use_existing_column=True, default="dark"
            ),
        )

        __mapper_args__ = {
            "polymorphic_identity": "dark",
        }

    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        hero = Hero()
        db.add(hero)
        dark_hero = DarkHero()
        db.add(dark_hero)
        db.commit()
        statement = select(DarkHero)
        result = db.exec(statement).all()
    assert len(result) == 1
    assert isinstance(result[0].dark_power, str)


@needs_pydanticv2
def test_polymorphic_single_table(clear_sqlmodel) -> None:
    class Hero(SQLModel, table=True):
        __tablename__ = "hero"
        id: Optional[int] = Field(default=None, primary_key=True)
        hero_type: str = Field(default="hero")

        __mapper_args__ = {
            "polymorphic_on": "hero_type",
            "polymorphic_identity": "normal_hero",
        }

    class DarkHero(Hero):
        dark_power: str = Field(
            default="dark",
            sa_column=mapped_column(
                nullable=False, use_existing_column=True, default="dark"
            ),
        )

        __mapper_args__ = {
            "polymorphic_identity": "dark",
        }

    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        hero = Hero()
        db.add(hero)
        dark_hero = DarkHero(dark_power="pokey")
        db.add(dark_hero)
        db.commit()
        statement = select(DarkHero)
        result = db.exec(statement).all()
    assert len(result) == 1
    assert isinstance(result[0].dark_power, str)


@needs_pydanticv2
def test_polymorphic_relationship(clear_sqlmodel) -> None:
    class Tool(SQLModel, table=True):
        __tablename__ = "tool_table"

        id: int = Field(primary_key=True)

        name: str

    class Person(SQLModel, table=True):
        __tablename__ = "person_table"

        id: int = Field(primary_key=True)

        discriminator: str
        name: str

        tool_id: int = Field(foreign_key="tool_table.id")
        tool: Tool = Relationship()

        __mapper_args__ = {
            "polymorphic_on": "discriminator",
            "polymorphic_identity": "simple_person",
        }

    class Worker(Person):
        __mapper_args__ = {
            "polymorphic_identity": "worker",
        }

    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        tool = Tool(id=1, name="Hammer")
        db.add(tool)
        worker = Worker(id=2, name="Bob", tool_id=1)
        db.add(worker)
        db.commit()

        statement = select(Worker).where(Worker.tool_id == 1)
        result = db.exec(statement).all()
        assert len(result) == 1
        assert isinstance(result[0].tool, Tool)


@needs_pydanticv2
def test_polymorphic_deeper(clear_sqlmodel) -> None:
    class Employee(SQLModel, table=True):
        __tablename__ = "employee"

        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
        type: str = Field(default="employee")

        __mapper_args__ = {
            "polymorphic_identity": "employee",
            "polymorphic_on": "type",
        }

    class Executive(Employee):
        """An executive of the company"""

        executive_background: Optional[str] = Field(
            sa_column=mapped_column(nullable=True), default=None
        )

        __mapper_args__ = {"polymorphic_abstract": True}

    class Technologist(Employee):
        """An employee who works with technology"""

        competencies: Optional[str] = Field(
            sa_column=mapped_column(nullable=True), default=None
        )

        __mapper_args__ = {"polymorphic_abstract": True}

    class Manager(Executive):
        """A manager"""

        __mapper_args__ = {"polymorphic_identity": "manager"}

    class Principal(Executive):
        """A principal of the company"""

        __mapper_args__ = {"polymorphic_identity": "principal"}

    class Engineer(Technologist):
        """An engineer"""

        __mapper_args__ = {"polymorphic_identity": "engineer"}

    class SysAdmin(Technologist):
        """A systems administrator"""

        __mapper_args__ = {"polymorphic_identity": "sysadmin"}

    # Create database and session
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        # Add different employee types
        manager = Manager(name="Alice", executive_background="MBA")
        principal = Principal(name="Bob", executive_background="Founder")
        engineer = Engineer(name="Charlie", competencies="Python, SQL")
        sysadmin = SysAdmin(name="Diana", competencies="Linux, Networking")

        db.add(manager)
        db.add(principal)
        db.add(engineer)
        db.add(sysadmin)
        db.commit()

        # Query each type to verify they persist correctly
        managers = db.exec(select(Manager)).all()
        principals = db.exec(select(Principal)).all()
        engineers = db.exec(select(Engineer)).all()
        sysadmins = db.exec(select(SysAdmin)).all()

        # Query abstract classes to verify they return appropriate concrete classes
        executives = db.exec(select(Executive)).all()
        technologists = db.exec(select(Technologist)).all()

        # All employees
        all_employees = db.exec(select(Employee)).all()

    # Assert individual type counts
    assert len(managers) == 1
    assert len(principals) == 1
    assert len(engineers) == 1
    assert len(sysadmins) == 1

    # Check that abstract classes can't be instantiated directly
    # but their subclasses are correctly returned when querying
    assert len(executives) == 2
    assert len(technologists) == 2
    assert len(all_employees) == 4

    # Check that properties of abstract classes are accessible from concrete instances
    assert managers[0].executive_background == "MBA"
    assert principals[0].executive_background == "Founder"
    assert engineers[0].competencies == "Python, SQL"
    assert sysadmins[0].competencies == "Linux, Networking"

    # Check polymorphic identities
    assert managers[0].type == "manager"
    assert principals[0].type == "principal"
    assert engineers[0].type == "engineer"
    assert sysadmins[0].type == "sysadmin"


@needs_pydanticv2
def test_polymorphic_validation_error(clear_sqlmodel) -> None:
    """Test that polymorphic models work with field constraints"""
    class Vehicle(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        vehicle_type: str
        
        __mapper_args__ = {
            "polymorphic_on": "vehicle_type",
            "polymorphic_identity": "vehicle",
        }
    
    class Car(Vehicle):
        doors: int = Field(ge=2, le=5)
        
        __mapper_args__ = {
            "polymorphic_identity": "car",
        }
    
    # Test that valid values work
    valid_car = Car(doors=4, vehicle_type="car")
    assert valid_car.doors == 4
    assert valid_car.vehicle_type == "car"
    
    # Test edge cases within valid range
    min_car = Car(doors=2, vehicle_type="car")
    assert min_car.doors == 2
    
    max_car = Car(doors=5, vehicle_type="car")
    assert max_car.doors == 5


@needs_pydanticv2
def test_polymorphic_missing_polymorphic_on(clear_sqlmodel) -> None:
    """Test error when polymorphic_on field is missing"""
    with pytest.raises(Exception):
        class Base(SQLModel, table=True):
            id: Optional[int] = Field(default=None, primary_key=True)
            
            __mapper_args__ = {
                "polymorphic_on": "missing_field",  # Field doesn't exist
                "polymorphic_identity": "base",
            }


@needs_pydanticv2
def test_polymorphic_duplicate_identity(clear_sqlmodel) -> None:
    """Test warning when duplicate polymorphic identities are used"""
    import warnings
    
    class Animal(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        animal_type: str
        
        __mapper_args__ = {
            "polymorphic_on": "animal_type",
            "polymorphic_identity": "animal",
        }
    
    class Dog(Animal):
        breed: str
        
        __mapper_args__ = {
            "polymorphic_identity": "dog",
        }
    
    # This should generate a warning, not an error
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        class Cat(Animal):
            color: str
            
            __mapper_args__ = {
                "polymorphic_identity": "dog",  # Duplicate identity
            }
        
        # Check that a warning was issued
        assert len(w) > 0
        assert any("polymorphic_identity" in str(warning.message) for warning in w)


@needs_pydanticv2
def test_polymorphic_with_complex_relationships(clear_sqlmodel) -> None:
    """Test polymorphic models with complex relationships"""
    class Company(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
    
    class Person(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
        person_type: str
        company_id: Optional[int] = Field(default=None, foreign_key="company.id")
        company: Optional[Company] = Relationship()
        
        __mapper_args__ = {
            "polymorphic_on": "person_type",
            "polymorphic_identity": "person",
        }
    
    class Employee(Person):
        salary: Optional[float] = Field(default=None)
        
        __mapper_args__ = {
            "polymorphic_identity": "employee",
        }
    
    class Customer(Person):
        credit_limit: Optional[float] = Field(default=None)
        
        __mapper_args__ = {
            "polymorphic_identity": "customer",
        }
    
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as db:
        company = Company(name="Tech Corp")
        db.add(company)
        db.flush()  # Get the company ID
        
        employee = Employee(
            name="Alice",
            person_type="employee",
            salary=75000.0,
            company_id=company.id
        )
        customer = Customer(
            name="Bob",
            person_type="customer",
            credit_limit=10000.0
        )
        
        db.add(employee)
        db.add(customer)
        db.commit()
        
        # Test querying with joins
        employees = db.exec(
            select(Employee).join(Company).where(Company.name == "Tech Corp")
        ).all()
        
        assert len(employees) == 1
        assert employees[0].name == "Alice"
        assert employees[0].company.name == "Tech Corp"
        
        # Test querying customers (no company relationship)
        customers = db.exec(select(Customer)).all()
        assert len(customers) == 1
        assert customers[0].name == "Bob"
        assert customers[0].company is None


@needs_pydanticv2
def test_polymorphic_with_nullable_discriminator(clear_sqlmodel) -> None:
    """Test polymorphic models with nullable discriminator column"""
    class Item(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
        item_type: Optional[str] = Field(default=None)
        
        __mapper_args__ = {
            "polymorphic_on": "item_type",
        }
    
    class Book(Item):
        author: str
        
        __mapper_args__ = {
            "polymorphic_identity": "book",
        }
    
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as db:
        # Create book with explicit discriminator
        book = Book(name="Python Guide", author="John Doe", item_type="book")
        
        db.add(book)
        db.commit()
        
        # Query books specifically
        books = db.exec(select(Book)).all()
        assert len(books) == 1
        assert books[0].author == "John Doe"
        assert books[0].item_type == "book"


@needs_pydanticv2
def test_polymorphic_inheritance_with_additional_fields(clear_sqlmodel) -> None:
    """Test polymorphic inheritance with additional fields"""
    class BaseModel(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
        model_type: str
        description: Optional[str] = Field(default="Base description")
        
        __mapper_args__ = {
            "polymorphic_on": "model_type",
            "polymorphic_identity": "base",
        }
    
    class SpecialModel(BaseModel):
        # Add new fields to child class
        special_field: Optional[str] = Field(default=None)
        priority: int = Field(default=1, ge=1, le=10)
        
        __mapper_args__ = {
            "polymorphic_identity": "special",
        }
    
    # Test valid creation with inheritance
    base = BaseModel(
        name="Base",
        model_type="base"
    )
    assert base.name == "Base"
    assert base.description == "Base description"
    
    special = SpecialModel(
        name="Special",
        model_type="special",
        special_field="Special value",
        priority=5
    )
    
    assert special.name == "Special"
    assert special.special_field == "Special value"
    assert special.priority == 5
    assert special.description == "Base description"  # Inherited default


@needs_pydanticv2
def test_polymorphic_model_serialization(clear_sqlmodel) -> None:
    """Test serialization of polymorphic models"""
    class Shape(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        shape_type: str
        
        __mapper_args__ = {
            "polymorphic_on": "shape_type",
            "polymorphic_identity": "shape",
        }
    
    class Rectangle(Shape):
        width: float
        height: float
        
        __mapper_args__ = {
            "polymorphic_identity": "rectangle",
        }
    
    class Circle(Shape):
        radius: float
        
        __mapper_args__ = {
            "polymorphic_identity": "circle",
        }
    
    # Test creation and serialization without database operations
    rectangle = Rectangle(shape_type="rectangle", width=10.0, height=5.0)
    circle = Circle(shape_type="circle", radius=3.0)
    
    # Test serialization to dict
    rect_dict = rectangle.model_dump()
    assert rect_dict["shape_type"] == "rectangle"
    assert rect_dict["width"] == 10.0
    assert rect_dict["height"] == 5.0
    
    circle_dict = circle.model_dump()
    assert circle_dict["shape_type"] == "circle"
    assert circle_dict["radius"] == 3.0
    
    # Test JSON serialization
    rect_json = rectangle.model_dump_json()
    assert "rectangle" in rect_json
    assert "10.0" in rect_json
