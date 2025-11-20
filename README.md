# Tourism Itinerary Planner

A mini-project developed as part of the DBMS course, the **Tourism Itinerary Planner** is a web-based application designed to simplify and personalize travel planning. It allows users to organize trips through structured, day-wise itineraries that include destinations, activities, transportation, and hotel details — all stored and managed through a robust SQL database.

---

## Features

### Itinerary Management
- Create day-wise itineraries  
- Add destinations with descriptions and ratings  
- Include activities with cost and duration  

###  Hotel & Booking System
- Store hotel information  
- Reference bookings inside itineraries  
- Check for conflicts and prevent double bookings  

###  Transport Options
- Add transport details like bus, train, flight, etc.  
- Linked to destination availability  

###  SQL Backend
Includes:
- Tables  
- Constraints  
- Triggers  
- Stored Procedures  
- Functions  
- Sample Data  

---

##  Project Structure
```
Tourism-Itinerary-Planner/
│
├── app.py
├── /templates
├── /static
├── /images
│
├── create_database.sql
├── test_triggers_functions.sql
└── README.md
```

---

##  Database Setup

Run in MySQL:
```sql
SOURCE create_database.sql;
SOURCE test_triggers_functions.sql;
```

---

##  Running the Application

1. Install Python (3.8+ recommended)
2. Install required libraries  
   *(Flask, MySQL connector — add if needed)*
3. Run:
```bash
   python app.py
```
4. Open in browser:
```
   http://127.0.0.1:5000/
```

---

##  Technologies Used

- **Python (Flask)**
- **HTML, CSS, JS**
- **MySQL Database**
- **Triggers, Procedures, Functions**
- **CRUD operations**

---

##  SQL Files Included

- **create_database.sql** → Creates tables + inserts sample data  
- **test_triggers_functions.sql** → Tests triggers, procedures, and functions  

---

##  Authors

**Sirisha Veluvolu**    
**Sneha Shetty**

---
