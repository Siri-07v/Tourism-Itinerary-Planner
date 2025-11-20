-- Travel Management System Database
-- Created for Database Management System Project

-- Drop database if it exists
DROP DATABASE IF EXISTS TravelManagementSystem;

-- Create database
CREATE DATABASE TravelManagementSystem;

-- Use the database
USE TravelManagementSystem;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS Booking CASCADE;
DROP TABLE IF EXISTS Activity CASCADE;
DROP TABLE IF EXISTS Transport CASCADE;
DROP TABLE IF EXISTS Availability CASCADE;
DROP TABLE IF EXISTS Includes CASCADE;
DROP TABLE IF EXISTS Destination CASCADE;
DROP TABLE IF EXISTS Itinerary CASCADE;
DROP TABLE IF EXISTS Hotel CASCADE;
DROP TABLE IF EXISTS User CASCADE;

-- User Table
CREATE TABLE User (
    UserID INT PRIMARY KEY AUTO_INCREMENT,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    PhoneNo VARCHAR(15) NOT NULL,
    Password VARCHAR(100) NOT NULL,
    CHECK (Email LIKE '%@%.%'),
    CHECK (PhoneNo REGEXP '^[0-9]{10,15}$')
);

-- Hotel Table
CREATE TABLE Hotel (
    HotelID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL UNIQUE,
    Location VARCHAR(100) NOT NULL,
    Rating INT CHECK (Rating >= 1 AND Rating <= 5),
    PricePerNight DECIMAL(10, 2) NOT NULL CHECK (PricePerNight > 0)
);

-- Destination Table
CREATE TABLE Destination (
    DestID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL UNIQUE,
    Location VARCHAR(100) NOT NULL,
    Type VARCHAR(50),
    Description VARCHAR(255),
    Rating INT CHECK (Rating >= 1 AND Rating <= 5),
    CHECK (Type IN ('Beach', 'Mountain', 'City', 'Heritage', 'Adventure', 'Religious'))
);

-- Availability Table
CREATE TABLE Availability (
    AvailabilityID INT PRIMARY KEY AUTO_INCREMENT,
    DestID INT NOT NULL,
    Cost DECIMAL(10, 2) NOT NULL CHECK (Cost > 0),
    FOREIGN KEY (DestID) REFERENCES Destination(DestID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Transport Table
CREATE TABLE Transport (
    TransportID INT PRIMARY KEY AUTO_INCREMENT,
    AvailabilityID INT NOT NULL,
    Type VARCHAR(50) NOT NULL,
    Provider VARCHAR(100) NOT NULL,
    Cost DECIMAL(10, 2) NOT NULL CHECK (Cost > 0),
    CHECK (Type IN ('Flight', 'Bus', 'Train', 'Car', 'Ship')),
    FOREIGN KEY (AvailabilityID) REFERENCES Availability(AvailabilityID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Activity Table
CREATE TABLE Activity (
    ActivityID INT PRIMARY KEY AUTO_INCREMENT,
    DestID INT NOT NULL,
    Name VARCHAR(100) NOT NULL,
    Description VARCHAR(255),
    Cost DECIMAL(10, 2) NOT NULL CHECK (Cost > 0),
    FOREIGN KEY (DestID) REFERENCES Destination(DestID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Itinerary Table
CREATE TABLE Itinerary (
    ItineraryID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT NOT NULL,
    Title VARCHAR(100) NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    TotalCost DECIMAL(12, 2) NOT NULL CHECK (TotalCost >= 0),
    CHECK (EndDate > StartDate),
    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Includes Table (Relationship between Itinerary and Destination - Many to Many)
CREATE TABLE Includes (
    ItineraryID INT NOT NULL,
    DestID INT NOT NULL,
    PRIMARY KEY (ItineraryID, DestID),
    FOREIGN KEY (ItineraryID) REFERENCES Itinerary(ItineraryID) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (DestID) REFERENCES Destination(DestID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Booking Table (Weak Entity - depends on User and Hotel)
CREATE TABLE Booking (
    BookingID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT NOT NULL,
    HotelID INT,
    CheckInDate DATE NOT NULL,
    CheckOutDate DATE NOT NULL,
    TotalPrice DECIMAL(12, 2) NOT NULL CHECK (TotalPrice > 0),
    BookingDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    BookingStatus VARCHAR(50) DEFAULT 'Confirmed' CHECK (BookingStatus IN ('Pending', 'Confirmed', 'Cancelled')),
    CHECK (CheckOutDate > CheckInDate),
    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Offers Table (Relationship/Junction Table between Hotel and Booking - Many to Many)
CREATE TABLE Offers (
    OfferID INT PRIMARY KEY AUTO_INCREMENT,
    HotelID INT NOT NULL,
    BookingID INT NOT NULL,
    Description VARCHAR(255),
    Rating INT CHECK (Rating >= 1 AND Rating <= 5),
    UNIQUE(HotelID, BookingID),
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================
-- INSERTING SAMPLE DATA
-- ============================================

-- Insert Users
INSERT INTO User (FirstName, LastName, Email, PhoneNo, Password) VALUES
('Aarav', 'Kumar', 'aarav.kumar@email.com', '9876543210', 'pass@123'),
('Priya', 'Sharma', 'priya.sharma@email.com', '9876543211', 'secure@456'),
('Rohan', 'Patel', 'rohan.patel@email.com', '9876543212', 'travel123'),
('Ananya', 'Singh', 'ananya.singh@email.com', '9876543213', 'adventurePass'),
('Vikram', 'Verma', 'vikram.verma@email.com', '9876543214', 'myPassword789');

-- Insert Hotels
INSERT INTO Hotel (Name, Location, Rating, PricePerNight) VALUES
('Taj Hotel', 'Bengaluru', 5, 5000.00),
('Radisson Blu', 'Mumbai', 4, 4500.00),
('The Lalit', 'New Delhi', 5, 5500.00),
('Hyatt Regency', 'Hyderabad', 4, 4000.00),
('Marriott Courtyard', 'Chennai', 3, 3500.00);

-- Insert Destinations
INSERT INTO Destination (Name, Location, Type, Description, Rating) VALUES
('Taj Mahal', 'Agra', 'Heritage', 'Historic monument and symbol of love', 5),
('Goa Beaches', 'Goa', 'Beach', 'Pristine beaches with water sports', 4),
('Kerala Backwaters', 'Kochi', 'Beach', 'Serene backwaters and houseboat rides', 5),
('Shimla Hills', 'Shimla', 'Mountain', 'Snow-covered mountains and trekking', 4),
('Mysore Palace', 'Mysore', 'Heritage', 'Magnificent palace with royal architecture', 4);

-- Insert Availability
INSERT INTO Availability (DestID, Cost) VALUES
(1, 2000.00),
(2, 1500.00),
(3, 2500.00),
(4, 1800.00),
(5, 1200.00);

-- Insert Transport
INSERT INTO Transport (AvailabilityID, Type, Provider, Cost) VALUES
(1, 'Train', 'Indian Railways', 800.00),
(2, 'Flight', 'IndiGo', 3000.00),
(3, 'Flight', 'Air India', 2500.00),
(4, 'Bus', 'Volvo Travels', 500.00),
(5, 'Train', 'South Central Railways', 600.00);

-- Insert Activities
INSERT INTO Activity (DestID, Name, Description, Cost) VALUES
(1, 'Guided Tour', 'Professional guide for Taj Mahal', 500.00),
(2, 'Scuba Diving', 'Underwater exploration', 2000.00),
(3, 'Houseboat Cruise', 'Backwater cruise with sunset view', 1500.00),
(4, 'Trekking', 'Mountain trekking adventure', 1200.00),
(5, 'Palace Tour', 'Guided tour of Mysore Palace', 400.00);

-- Insert Itineraries
INSERT INTO Itinerary (UserID, Title, StartDate, EndDate, TotalCost) VALUES
(1, 'Golden Triangle Tour', '2025-01-15', '2025-01-22', 15000.00),
(2, 'Goa and Kerala Adventure', '2025-02-01', '2025-02-10', 25000.00),
(3, 'Himalayan Escape', '2025-02-15', '2025-02-20', 12000.00),
(4, 'South India Explorer', '2025-03-01', '2025-03-08', 18000.00),
(5, 'Heritage Trail', '2025-03-10', '2025-03-15', 9500.00);

-- Insert Includes (Itinerary includes Destinations)
INSERT INTO Includes (ItineraryID, DestID) VALUES
(1, 1),
(1, 5),
(2, 2),
(2, 3),
(3, 4),
(4, 1),
(4, 2),
(4, 3),
(5, 5);

-- Insert Bookings (Weak Entity)
INSERT INTO Booking (UserID, HotelID, CheckInDate, CheckOutDate, TotalPrice, BookingStatus) VALUES
(1, 1, '2025-01-15', '2025-01-20', 25000.00, 'Confirmed'),
(2, 2, '2025-02-01', '2025-02-08', 31500.00, 'Confirmed'),
(3, 3, '2025-02-15', '2025-02-18', 16500.00, 'Pending'),
(4, 4, '2025-03-01', '2025-03-06', 20000.00, 'Confirmed'),
(5, 5, '2025-03-10', '2025-03-13', 10500.00, 'Confirmed');

-- Insert Offers (Relationship table between Hotel and Booking)
INSERT INTO Offers (HotelID, BookingID, Description, Rating) VALUES
(1, 1, 'Early bird discount - 20% off', 5),
(2, 2, 'Student Discount', 4),
(3, 3, 'Business traveler special - complimentary breakfast', 5),
(4, 4, 'Weekend getaway - 15% discount', 4),
(5, 5, 'Group booking offer - 10% off for 5+ rooms', 3);

-- ============================================
-- DISPLAY ALL TABLES
-- ============================================

SELECT '=== USER TABLE ===' AS '';
SELECT * FROM User;

SELECT '=== HOTEL TABLE ===' AS '';
SELECT * FROM Hotel;

SELECT '=== DESTINATION TABLE ===' AS '';
SELECT * FROM Destination;

SELECT '=== AVAILABILITY TABLE ===' AS '';
SELECT * FROM Availability;

SELECT '=== TRANSPORT TABLE ===' AS '';
SELECT * FROM Transport;

SELECT '=== ACTIVITY TABLE ===' AS '';
SELECT * FROM Activity;

SELECT '=== ITINERARY TABLE ===' AS '';
SELECT * FROM Itinerary;

SELECT '=== INCLUDES TABLE ===' AS '';
SELECT * FROM Includes;

SELECT '=== BOOKING TABLE ===' AS '';
SELECT * FROM Booking;

SELECT '=== OFFERS TABLE ===' AS '';
SELECT * FROM Offers;