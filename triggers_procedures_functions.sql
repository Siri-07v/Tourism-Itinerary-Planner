-- Travel Itinerary Management System - Advanced SQL
-- Triggers, Procedures, and Functions
-- Use existing TravelManagementSystem database

USE TravelManagementSystem;

-- ============================================
-- DROP EXISTING FUNCTIONS, PROCEDURES, TRIGGERS
-- ============================================

DROP TRIGGER IF EXISTS UpdateUserBookingCount_INSERT;
DROP TRIGGER IF EXISTS AuditBookingStatusChange;
DROP TRIGGER IF EXISTS CreatePaymentOnBooking;
DROP TRIGGER IF EXISTS PreventOverbooking;

DROP PROCEDURE IF EXISTS CreateNewBooking;
DROP PROCEDURE IF EXISTS CancelBooking;
DROP PROCEDURE IF EXISTS GetBookingDetails;
DROP PROCEDURE IF EXISTS GetDestinationItineraries;

DROP FUNCTION IF EXISTS CalculateBookingCost;
DROP FUNCTION IF EXISTS GetUserTotalSpending;
DROP FUNCTION IF EXISTS IsDestinationPopular;

-- Add TotalBookings column to User if it doesn't exist
ALTER TABLE User ADD COLUMN TotalBookings INT DEFAULT 0;

-- Create audit table if not exists
CREATE TABLE IF NOT EXISTS BookingAudit (
    AuditID INT PRIMARY KEY AUTO_INCREMENT,
    BookingID INT NOT NULL,
    ActionType VARCHAR(50),
    OldStatus VARCHAR(50),
    NewStatus VARCHAR(50),
    ChangeDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UserEmail VARCHAR(100)
);

-- Create payment transaction table if not exists
CREATE TABLE IF NOT EXISTS PaymentTransaction (
    TransactionID INT PRIMARY KEY AUTO_INCREMENT,
    BookingID INT NOT NULL,
    Amount DECIMAL(12, 2) NOT NULL,
    PaymentStatus VARCHAR(50) DEFAULT 'Pending' CHECK (PaymentStatus IN ('Pending', 'Completed', 'Failed')),
    TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================
-- FUNCTIONS
-- ============================================

-- FUNCTION 1: Calculate total booking cost based on hotel and dates
DELIMITER //
CREATE FUNCTION CalculateBookingCost(p_HotelID INT, p_CheckInDate DATE, p_CheckOutDate DATE) 
RETURNS DECIMAL(12, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_PricePerNight DECIMAL(10, 2);
    DECLARE v_NumberOfNights INT;
    DECLARE v_TotalCost DECIMAL(12, 2);
    
    -- Get the price per night for the hotel
    SELECT PricePerNight INTO v_PricePerNight FROM Hotel WHERE HotelID = p_HotelID;
    
    -- Calculate number of nights
    SET v_NumberOfNights = DATEDIFF(p_CheckOutDate, p_CheckInDate);
    
    -- Calculate total cost
    SET v_TotalCost = v_PricePerNight * v_NumberOfNights;
    
    RETURN v_TotalCost;
END //
DELIMITER ;

-- FUNCTION 2: Get user's total spending on confirmed bookings
DELIMITER //
CREATE FUNCTION GetUserTotalSpending(p_UserID INT) 
RETURNS DECIMAL(12, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_TotalSpending DECIMAL(12, 2);
    
    SELECT COALESCE(SUM(TotalPrice), 0) INTO v_TotalSpending 
    FROM Booking 
    WHERE UserID = p_UserID AND BookingStatus = 'Confirmed';
    
    RETURN v_TotalSpending;
END //
DELIMITER ;

-- FUNCTION 3: Check if destination is popular based on number of itineraries
DELIMITER //
CREATE FUNCTION IsDestinationPopular(p_DestID INT) 
RETURNS VARCHAR(50)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_VisitCount INT;
    
    SELECT COUNT(*) INTO v_VisitCount 
    FROM Includes 
    WHERE DestID = p_DestID;
    
    IF v_VisitCount >= 3 THEN
        RETURN 'Popular';
    ELSEIF v_VisitCount >= 1 THEN
        RETURN 'Moderate';
    ELSE
        RETURN 'Not Popular';
    END IF;
END //
DELIMITER ;

-- ============================================
-- PROCEDURES
-- ============================================

-- PROCEDURE 1: Create a new booking with validation
DELIMITER //
CREATE PROCEDURE CreateNewBooking(
    IN p_UserID INT,
    IN p_HotelID INT,
    IN p_CheckInDate DATE,
    IN p_CheckOutDate DATE,
    OUT p_BookingID INT,
    OUT p_TotalPrice DECIMAL(12, 2),
    OUT p_Message VARCHAR(255)
)
BEGIN
    DECLARE v_ExistingBooking INT;
    
    -- Start Transaction
    START TRANSACTION;
    
    -- Check if user has conflicting bookings
    SELECT COUNT(*) INTO v_ExistingBooking 
    FROM Booking 
    WHERE UserID = p_UserID 
    AND BookingStatus = 'Confirmed'
    AND (
        (CheckInDate <= p_CheckOutDate AND CheckOutDate >= p_CheckInDate)
    );
    
    IF v_ExistingBooking > 0 THEN
        SET p_Message = 'User has conflicting bookings on these dates';
        SET p_BookingID = 0;
        SET p_TotalPrice = 0;
        -- Rollback transaction if there's a conflict
        ROLLBACK;
    ELSE
        -- Calculate total cost using function
        SET p_TotalPrice = CalculateBookingCost(p_HotelID, p_CheckInDate, p_CheckOutDate);
        
        -- Insert new booking
        INSERT INTO Booking (UserID, HotelID, CheckInDate, CheckOutDate, TotalPrice, BookingStatus)
        VALUES (p_UserID, p_HotelID, p_CheckInDate, p_CheckOutDate, p_TotalPrice, 'Confirmed');
        
        SET p_BookingID = LAST_INSERT_ID();
        SET p_Message = 'Booking created successfully';
        
        -- Commit transaction if all steps are successful
        COMMIT;
    END IF;
END //
DELIMITER ;

-- PROCEDURE 2: Cancel booking and update status
DELIMITER //
CREATE PROCEDURE CancelBooking(
    IN p_BookingID INT,
    OUT p_Message VARCHAR(255)
)
BEGIN
    DECLARE v_CurrentStatus VARCHAR(50);
    DECLARE v_UserID INT;
    
    -- Start Transaction
    START TRANSACTION;
    
    -- Get current booking status
    SELECT BookingStatus, UserID INTO v_CurrentStatus, v_UserID 
    FROM Booking 
    WHERE BookingID = p_BookingID;
    
    IF v_CurrentStatus IS NULL THEN
        SET p_Message = 'Booking does not exist';
        -- Rollback if booking does not exist
        ROLLBACK;
    ELSEIF v_CurrentStatus = 'Cancelled' THEN
        SET p_Message = 'Booking is already cancelled';
        -- Rollback if booking is already cancelled
        ROLLBACK;
    ELSEIF v_CurrentStatus = 'Confirmed' THEN
        UPDATE Booking SET BookingStatus = 'Cancelled' WHERE BookingID = p_BookingID;
        SET p_Message = 'Booking cancelled successfully';
        
        -- Commit transaction if cancellation is successful
        COMMIT;
    ELSE
        SET p_Message = CONCAT('Cannot cancel booking with status: ', v_CurrentStatus);
        -- Rollback if status is not suitable for cancellation
        ROLLBACK;
    END IF;
END //
DELIMITER ;

-- PROCEDURE 3: Get booking details with all related information
DELIMITER //
CREATE PROCEDURE GetBookingDetails(
    IN p_BookingID INT
)
BEGIN
    SELECT 
        b.BookingID,
        CONCAT(u.FirstName, ' ', u.LastName) AS UserName,
        u.Email,
        h.Name AS HotelName,
        h.Location,
        h.Rating AS HotelRating,
        h.PricePerNight,
        b.CheckInDate,
        b.CheckOutDate,
        DATEDIFF(b.CheckOutDate, b.CheckInDate) AS NumberOfNights,
        b.TotalPrice,
        b.BookingStatus,
        b.BookingDate
    FROM Booking b
    LEFT JOIN User u ON b.UserID = u.UserID
    LEFT JOIN Hotel h ON b.HotelID = h.HotelID
    WHERE b.BookingID = p_BookingID;
END //
DELIMITER ;

-- PROCEDURE 4: Get all itineraries for a destination
DELIMITER //
CREATE PROCEDURE GetDestinationItineraries(
    IN p_DestID INT
)
BEGIN
    SELECT DISTINCT
        i.ItineraryID,
        i.Title,
        CONCAT(u.FirstName, ' ', u.LastName) AS CreatedBy,
        i.StartDate,
        i.EndDate,
        DATEDIFF(i.EndDate, i.StartDate) AS DurationDays,
        i.TotalCost,
        d.Name AS DestinationName,
        d.Type,
        d.Rating
    FROM Itinerary i
    JOIN Includes inc ON i.ItineraryID = inc.ItineraryID
    JOIN Destination d ON inc.DestID = d.DestID
    JOIN User u ON i.UserID = u.UserID
    WHERE d.DestID = p_DestID
    ORDER BY i.StartDate;
END //
DELIMITER ;

-- ============================================
-- TRIGGERS
-- ============================================

-- TRIGGER 1: Update user's total bookings count when new booking is created
DELIMITER //
CREATE TRIGGER UpdateUserBookingCount_INSERT
AFTER INSERT ON Booking
FOR EACH ROW
BEGIN
    UPDATE User 
    SET TotalBookings = TotalBookings + 1 
    WHERE UserID = NEW.UserID;
END //
DELIMITER ;

-- TRIGGER 2: Create automatic payment record when booking is confirmed
DELIMITER //
CREATE TRIGGER CreatePaymentOnBooking
AFTER INSERT ON Booking
FOR EACH ROW
BEGIN
    IF NEW.BookingStatus = 'Confirmed' THEN
        INSERT INTO PaymentTransaction (BookingID, Amount, PaymentStatus)
        VALUES (NEW.BookingID, NEW.TotalPrice, 'Pending');
    END IF;
END //
DELIMITER ;

-- TRIGGER 3: Prevent overbooking by checking hotel availability on insert
DELIMITER //
CREATE TRIGGER PreventOverbooking
BEFORE INSERT ON Booking
FOR EACH ROW
BEGIN
    DECLARE v_ConflictCount INT;
    
    SELECT COUNT(*) INTO v_ConflictCount
    FROM Booking
    WHERE HotelID = NEW.HotelID
    AND BookingStatus = 'Confirmed'
    AND (
        (CheckInDate < NEW.CheckOutDate AND CheckOutDate > NEW.CheckInDate)
    );
    
    IF v_ConflictCount > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Hotel is not available for selected dates';
    END IF;
END //
DELIMITER ;

-- ============================================
-- FUNCTION 1 TESTING
-- ============================================

SELECT '*** FUNCTION 1: CalculateBookingCost ***' AS TEST;
SELECT CalculateBookingCost(1, '2025-01-15', '2025-01-20') AS 'Taj Hotel (5 nights)';
SELECT CalculateBookingCost(2, '2025-02-01', '2025-02-08') AS 'Radisson Blu (7 nights)';
SELECT CalculateBookingCost(3, '2025-02-15', '2025-02-18') AS 'The Lalit (3 nights)';

-- ============================================
-- FUNCTION 2 TESTING
-- ============================================

SELECT '*** FUNCTION 2: GetUserTotalSpending ***' AS TEST;
SELECT 
    UserID,
    CONCAT(FirstName, ' ', LastName) AS UserName,
    Email,
    GetUserTotalSpending(UserID) AS TotalSpending
FROM User;

-- ============================================
-- FUNCTION 3 TESTING
-- ============================================

SELECT '*** FUNCTION 3: IsDestinationPopular ***' AS TEST;
SELECT 
    DestID,
    Name AS DestinationName,
    Location,
    IsDestinationPopular(DestID) AS PopularityStatus
FROM Destination;

-- ============================================
-- PROCEDURE 1 TESTING
-- ============================================

SELECT '*** PROCEDURE 1: CreateNewBooking ***' AS TEST;
CALL CreateNewBooking(1, 5, '2025-04-01', '2025-04-05', @BookingID, @TotalPrice, @Message);
SELECT @BookingID AS NewBookingID, @TotalPrice AS TotalPrice, @Message AS Status;

-- ============================================
-- PROCEDURE 2 TESTING
-- ============================================

SELECT '*** PROCEDURE 2: GetBookingDetails (Booking ID 1) ***' AS TEST;
CALL GetBookingDetails(1);

-- ============================================
-- PROCEDURE 3 TESTING
-- ============================================

SELECT '*** PROCEDURE 3: CancelBooking (Booking ID 3) ***' AS TEST;
SELECT 'BEFORE CANCELLATION:' AS Status;
CALL GetBookingDetails(3);

CALL CancelBooking(3, @CancelMsg);
SELECT @CancelMsg AS CancellationResult;

SELECT 'AFTER CANCELLATION:' AS Status;
CALL GetBookingDetails(3);

-- ============================================
-- PROCEDURE 4 TESTING
-- ============================================

SELECT '*** PROCEDURE 4: GetDestinationItineraries (Taj Mahal - DestID 1) ***' AS TEST;
CALL GetDestinationItineraries(1);

-- ============================================
-- TRIGGER RESULTS
-- ============================================
-- TEST TRIGGER 1: UpdateUserBookingCount_INSERT
SELECT '*** TEST TRIGGER 1: UpdateUserBookingCount_INSERT ***' AS '';
SELECT 'BEFORE: User 1 TotalBookings' AS '';
SELECT UserID, TotalBookings FROM User WHERE UserID = 1;

SELECT 'Creating new booking for User 1...' AS '';
CALL CreateNewBooking(1, 5, '2025-04-10', '2025-04-12', @BID, @BP, @BM);

SELECT 'AFTER: User 1 TotalBookings (should increase by 1)' AS '';
SELECT UserID, TotalBookings FROM User WHERE UserID = 1;

-- TEST TRIGGER 2: CreatePaymentOnBooking
SELECT '' AS '';
SELECT '*** TEST TRIGGER 2: CreatePaymentOnBooking ***' AS '';
SELECT 'PaymentTransaction records created automatically:' AS '';
SELECT * FROM PaymentTransaction ORDER BY TransactionID DESC LIMIT 3;

-- TEST TRIGGER 3: PreventOverbooking
SELECT '' AS '';
SELECT '*** TEST TRIGGER 3: PreventOverbooking ***' AS '';
SELECT 'Trying to book SAME hotel on SAME dates (should fail)...' AS '';
-- This will error (expected):
CALL CreateNewBooking(2, 1, '2025-01-15', '2025-01-20', @BID2, @BP2, @BM2);
-- ERROR: Hotel is not available for selected dates
