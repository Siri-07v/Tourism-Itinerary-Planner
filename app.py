from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this'  # Change this in production
CORS(app)

# ============================================
# STATIC FILES - IMAGES
# ============================================
@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from the images folder"""
    return send_from_directory('images', filename)

# ============================================
# DATABASE CONNECTION
# ============================================
def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',           # Change if needed
            user='root',                # Your MySQL username
            password='Sneha@123',   # Your MySQL password
            database='travelmanagementsystem'
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# ============================================
# DATABASE INITIALIZATION - TRIGGERS, FUNCTIONS, PROCEDURES
# ============================================
# NOTE: All triggers, functions, and procedures should be created in the database
# using the provided SQL script before running this application.
#
# TRIGGERS (Execute automatically on database events):
# 1. UpdateUserBookingCount_INSERT - Updates User.TotalBookings when booking is created

# 2. PreventOverbooking - Prevents booking if hotel is already booked for those dates
# 3. AuditBookingStatusChange - Logs status changes to BookingAudit table (if created)
#
# FUNCTIONS (Called via SQL queries):
# 1. CalculateBookingCost(hotelId, checkIn, checkOut) - Used in /booking/calculate-cost
# 2. GetUserTotalSpending(userId) - Used in /reports/user-spending
# 3. IsDestinationPopular(destId) - Used in /destination/popularity and /reports/popular-destinations
#
# PROCEDURES (Called via cursor.callproc):
# 1. CreateNewBooking - Used in /booking/create (triggers fire automatically)
# 2. CancelBooking - Used in /booking/cancel (triggers fire automatically)
# 3. GetBookingDetails - Used in /booking/details
# 4. GetDestinationItineraries - Used in /destination/itineraries
#
def initialize_database_objects():
    """Ensure required tables, columns, functions, procedures, and triggers exist"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Database initialization skipped: unable to connect.")
            return False

        cursor = conn.cursor()

        drop_statements = [
            "DROP TRIGGER IF EXISTS UpdateUserBookingCount_INSERT",
            "DROP TRIGGER IF EXISTS AuditBookingStatusChange",
            "DROP TRIGGER IF EXISTS PreventOverbooking",
            "DROP PROCEDURE IF EXISTS CreateNewBooking",
            "DROP PROCEDURE IF EXISTS CancelBooking",
            "DROP PROCEDURE IF EXISTS GetBookingDetails",
            "DROP PROCEDURE IF EXISTS GetDestinationItineraries",
            "DROP FUNCTION IF EXISTS CalculateBookingCost",
            "DROP FUNCTION IF EXISTS GetUserTotalSpending",
            "DROP FUNCTION IF EXISTS IsDestinationPopular",
        ]

        # Ensure supporting schema exists before recreating routines
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'User'
              AND COLUMN_NAME = 'TotalBookings'
            """,
            (conn.database,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE User ADD COLUMN TotalBookings INT DEFAULT 0")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'Hotel'
              AND COLUMN_NAME = 'AvailableRooms'
            """,
            (conn.database,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE Hotel ADD COLUMN AvailableRooms INT DEFAULT 0")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'EmailLog'
              AND COLUMN_NAME = 'RecipientEmail'
            """,
            (conn.database,)
        )
        emaillog_has_column = cursor.fetchone()[0] > 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'EmailLog'
              AND COLUMN_NAME = 'RecipientName'
            """,
            (conn.database,)
        )
        emaillog_has_recipient_name = cursor.fetchone()[0] > 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'EmailLog'
              AND COLUMN_NAME = 'Message'
            """,
            (conn.database,)
        )
        emaillog_has_message = cursor.fetchone()[0] > 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'EmailLog'
              AND COLUMN_NAME = 'SentAt'
            """,
            (conn.database,)
        )
        emaillog_has_sent_at = cursor.fetchone()[0] > 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'EmailLog'
              AND COLUMN_NAME = 'Status'
            """,
            (conn.database,)
        )
        emaillog_has_status = cursor.fetchone()[0] > 0

        create_statements = [
            """
            CREATE TABLE IF NOT EXISTS EmailLog (
                EmailID INT PRIMARY KEY AUTO_INCREMENT,
                Recipient VARCHAR(255) NOT NULL,
                Subject VARCHAR(255),
                Body TEXT,
                SentDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                SentAt TIMESTAMP NULL DEFAULT NULL,
                Status VARCHAR(50) DEFAULT 'Pending'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS BookingAudit (
                AuditID INT PRIMARY KEY AUTO_INCREMENT,
                BookingID INT NOT NULL,
                ActionType VARCHAR(50),
                OldStatus VARCHAR(50),
                NewStatus VARCHAR(50),
                ChangeDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UserEmail VARCHAR(100)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS PaymentTransaction (
                TransactionID INT PRIMARY KEY AUTO_INCREMENT,
                BookingID INT NOT NULL,
                Amount DECIMAL(12, 2) NOT NULL,
                PaymentStatus VARCHAR(50) DEFAULT 'Pending' CHECK (PaymentStatus IN ('Pending', 'Completed', 'Failed')),
                TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (BookingID) REFERENCES Booking(BookingID) ON DELETE CASCADE ON UPDATE CASCADE
            )
            """,
            # Functions
            """
            CREATE FUNCTION CalculateBookingCost(p_HotelID INT, p_CheckInDate DATE, p_CheckOutDate DATE)
            RETURNS DECIMAL(12, 2)
            DETERMINISTIC
            READS SQL DATA
            BEGIN
                DECLARE v_PricePerNight DECIMAL(10, 2);
                DECLARE v_NumberOfNights INT;
                DECLARE v_TotalCost DECIMAL(12, 2);

                SELECT PricePerNight INTO v_PricePerNight FROM Hotel WHERE HotelID = p_HotelID;
                SET v_NumberOfNights = DATEDIFF(p_CheckOutDate, p_CheckInDate);
                SET v_TotalCost = v_PricePerNight * v_NumberOfNights;

                RETURN v_TotalCost;
            END
            """,
            """
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
            END
            """,
            """
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
            END
            """,
            # Procedures
            """
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

                START TRANSACTION;

                SELECT COUNT(*) INTO v_ExistingBooking
                FROM Booking
                WHERE UserID = p_UserID
                AND BookingStatus = 'Confirmed'
                AND ((CheckInDate <= p_CheckOutDate AND CheckOutDate >= p_CheckInDate));

                IF v_ExistingBooking > 0 THEN
                    SET p_Message = 'User has conflicting bookings on these dates';
                    SET p_BookingID = 0;
                    SET p_TotalPrice = 0;
                    ROLLBACK;
                ELSE
                    SET p_TotalPrice = CalculateBookingCost(p_HotelID, p_CheckInDate, p_CheckOutDate);

                    INSERT INTO Booking (UserID, HotelID, CheckInDate, CheckOutDate, TotalPrice, BookingStatus)
                    VALUES (p_UserID, p_HotelID, p_CheckInDate, p_CheckOutDate, p_TotalPrice, 'Confirmed');

                    SET p_BookingID = LAST_INSERT_ID();
                    SET p_Message = 'Booking created successfully';

                    COMMIT;
                END IF;
            END
            """,
            """
            CREATE PROCEDURE CancelBooking(
                IN p_BookingID INT,
                OUT p_Message VARCHAR(255)
            )
            BEGIN
                DECLARE v_CurrentStatus VARCHAR(50);

                START TRANSACTION;

                SELECT BookingStatus INTO v_CurrentStatus
                FROM Booking
                WHERE BookingID = p_BookingID;

                IF v_CurrentStatus IS NULL THEN
                    SET p_Message = 'Booking does not exist';
                    ROLLBACK;
                ELSEIF v_CurrentStatus = 'Cancelled' THEN
                    SET p_Message = 'Booking is already cancelled';
                    ROLLBACK;
                ELSEIF v_CurrentStatus = 'Confirmed' THEN
                    UPDATE Booking SET BookingStatus = 'Cancelled' WHERE BookingID = p_BookingID;
                    SET p_Message = 'Booking cancelled successfully';
                    COMMIT;
                ELSE
                    SET p_Message = CONCAT('Cannot cancel booking with status: ', v_CurrentStatus);
                    ROLLBACK;
                END IF;
            END
            """,
            """
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
            END
            """,
            """
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
            END
            """,
            # Triggers
            """
            CREATE TRIGGER UpdateUserBookingCount_INSERT
            AFTER INSERT ON Booking
            FOR EACH ROW
            BEGIN
                UPDATE User
                SET TotalBookings = TotalBookings + 1
                WHERE UserID = NEW.UserID;
            END
            """,
            """
            CREATE TRIGGER PreventOverbooking
            BEFORE INSERT ON Booking
            FOR EACH ROW
            BEGIN
                DECLARE v_ConflictCount INT;

                SELECT COUNT(*) INTO v_ConflictCount
                FROM Booking
                WHERE HotelID = NEW.HotelID
                AND BookingStatus = 'Confirmed'
                AND ((CheckInDate < NEW.CheckOutDate AND CheckOutDate > NEW.CheckInDate));

                IF v_ConflictCount > 0 THEN
                    SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Hotel is not available for selected dates';
                END IF;
            END
            """,
            """
            CREATE TRIGGER AuditBookingStatusChange
            AFTER UPDATE ON Booking
            FOR EACH ROW
            BEGIN
                DECLARE v_UserEmail VARCHAR(100);

                IF NEW.BookingStatus <> OLD.BookingStatus THEN
                    SELECT Email INTO v_UserEmail FROM User WHERE UserID = OLD.UserID LIMIT 1;

                    INSERT INTO BookingAudit (BookingID, ActionType, OldStatus, NewStatus, UserEmail)
                    VALUES (OLD.BookingID, 'Status Change', OLD.BookingStatus, NEW.BookingStatus, v_UserEmail);
                END IF;
            END
            """,
        ]

        for statement in drop_statements:
            cursor.execute(statement)

        for statement in create_statements:
            cursor.execute(statement)

        if not emaillog_has_column:
            cursor.execute("ALTER TABLE EmailLog ADD COLUMN RecipientEmail VARCHAR(255)")
        if not emaillog_has_recipient_name:
            cursor.execute("ALTER TABLE EmailLog ADD COLUMN RecipientName VARCHAR(255)")
        if not emaillog_has_message:
            cursor.execute("ALTER TABLE EmailLog ADD COLUMN Message TEXT")
        if not emaillog_has_sent_at:
            cursor.execute("ALTER TABLE EmailLog ADD COLUMN SentAt TIMESTAMP NULL DEFAULT NULL")
        if not emaillog_has_status:
            cursor.execute("ALTER TABLE EmailLog ADD COLUMN Status VARCHAR(50) DEFAULT 'Pending'")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database routines/triggers ensured.")
        return True
    except mysql.connector.Error as err:
        print(f"Database initialization error: {err}")
        return False

# Ensure database objects are present when the app starts
initialize_database_objects()

# ============================================
# ROUTES - USER MANAGEMENT
# ============================================

@app.route('/')
def index():
    """Landing page - Login/Register"""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """Register new user (CREATE - User table)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert new user
        query = """
        INSERT INTO User (FirstName, LastName, Email, PhoneNo, Password)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['firstName'],
            data['lastName'],
            data['email'],
            data['phone'],
            data['password']  # In production, hash this password!
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'userId': user_id
        })
        
    except mysql.connector.Error as err:
        return jsonify({
            'success': False,
            'message': f'Error: {str(err)}'
        }), 400

@app.route('/login', methods=['POST'])
def login():
    """User login (READ - User table)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check user credentials
        query = "SELECT * FROM User WHERE Email = %s AND Password = %s"
        cursor.execute(query, (data['email'], data['password']))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user:
            # Store user info in session
            session['user_id'] = user['UserID']
            session['user_name'] = f"{user['FirstName']} {user['LastName']}"
            
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'user': {
                    'id': user['UserID'],
                    'name': f"{user['FirstName']} {user['LastName']}",
                    'email': user['Email']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
            
    except mysql.connector.Error as err:
        return jsonify({
            'success': False,
            'message': f'Error: {str(err)}'
        }), 400

@app.route('/user/profile/<int:user_id>')
def get_user_profile(user_id):
    """Get user profile details (READ)
    Note: TotalBookings is calculated as count of confirmed bookings only
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user details
        query = "SELECT UserID, FirstName, LastName, Email, PhoneNo FROM User WHERE UserID = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Calculate confirmed bookings count
            count_query = """
                SELECT COUNT(*) as ConfirmedBookings 
                FROM Booking 
                WHERE UserID = %s AND BookingStatus = 'Confirmed'
            """
            cursor.execute(count_query, (user_id,))
            booking_count = cursor.fetchone()
            
            # Add confirmed bookings count to user data
            user['TotalBookings'] = booking_count['ConfirmedBookings'] if booking_count else 0
        
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({'success': True, 'user': user})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/user/update/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user profile (UPDATE - User table)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        UPDATE User 
        SET FirstName = %s, LastName = %s, PhoneNo = %s
        WHERE UserID = %s
        """
        cursor.execute(query, (
            data['firstName'],
            data['lastName'],
            data['phone'],
            user_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# ROUTES - BOOKING MANAGEMENT (CRUD + Procedures)
# ============================================

@app.route('/hotels')
def get_hotels():
    """Get all hotels for booking dropdown"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM Hotel ORDER BY Name"
        cursor.execute(query)
        hotels = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'hotels': hotels})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/booking/calculate-cost', methods=['POST'])
def calculate_booking_cost():
    """Calculate booking cost using FUNCTION (CalculateBookingCost)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Call the MySQL function
        query = "SELECT CalculateBookingCost(%s, %s, %s) as total_cost"
        cursor.execute(query, (
            data['hotelId'],
            data['checkInDate'],
            data['checkOutDate']
        ))
        
        result = cursor.fetchone()
        total_cost = result[0] if result else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'totalCost': float(total_cost)
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/booking/create', methods=['POST'])
def create_booking():
    """Create new booking using STORED PROCEDURE (CreateNewBooking)
    Triggers will execute automatically:
    - PreventOverbooking: Checks hotel availability BEFORE insert
    - UpdateUserBookingCount_INSERT: Updates user's total bookings AFTER insert
    """
    try:
        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        
        # Call stored procedure
        # Note: PreventOverbooking trigger will fire BEFORE insert and prevent overbooking
        args = [
            data['userId'],
            data['hotelId'],
            data['checkInDate'],
            data['checkOutDate'],
            0,  # OUT parameter: BookingID
            0,  # OUT parameter: TotalPrice
            ''  # OUT parameter: Message
        ]
        
        result = cursor.callproc('CreateNewBooking', args)
        
        # Get OUT parameters
        booking_id = result[4]
        total_price = result[5]
        message = result[6]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': booking_id > 0,
            'message': message,
            'bookingId': booking_id,
            'totalPrice': float(total_price)
        })
        
    except mysql.connector.Error as err:
        error_msg = str(err)
        error_code = err.errno if hasattr(err, 'errno') else None
        
        # Handle trigger errors (PreventOverbooking trigger raises SQLSTATE 45000)
        if '45000' in error_msg or 'Hotel is not available' in error_msg or 'not available for selected dates' in error_msg:
            return jsonify({
                'success': False,
                'message': 'Hotel is not available for selected dates. Please choose different dates.'
            }), 400
        
        # Handle other database errors
        return jsonify({
            'success': False,
            'message': f'Error: {error_msg}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/booking/details/<int:booking_id>')
def get_booking_details(booking_id):
    """Get booking details using STORED PROCEDURE (GetBookingDetails)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Call stored procedure
        cursor.callproc('GetBookingDetails', [booking_id])
        
        # Fetch results
        for result in cursor.stored_results():
            booking = result.fetchone()
        
        cursor.close()
        conn.close()
        
        if booking:
            return jsonify({'success': True, 'booking': booking})
        else:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
            
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/bookings/user/<int:user_id>')
def get_user_bookings(user_id):
    """Get all bookings for a user (READ - with JOIN)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            b.BookingID,
            b.CheckInDate,
            b.CheckOutDate,
            b.TotalPrice,
            b.BookingStatus,
            b.BookingDate,
            h.Name AS HotelName,
            h.Location AS HotelLocation,
            h.Rating AS HotelRating
        FROM Booking b
        LEFT JOIN Hotel h ON b.HotelID = h.HotelID
        WHERE b.UserID = %s
        ORDER BY b.BookingDate DESC
        """
        cursor.execute(query, (user_id,))
        bookings = cursor.fetchall()
        
        # Format dates to ensure consistent YYYY-MM-DD format
        for booking in bookings:
            # Format CheckInDate
            if booking['CheckInDate']:
                if isinstance(booking['CheckInDate'], (datetime, date)):
                    booking['CheckInDate'] = booking['CheckInDate'].strftime('%Y-%m-%d')
                elif isinstance(booking['CheckInDate'], str) and booking['CheckInDate'].strip() not in ('None', 'null', 'NULL', ''):
                    # Try to parse and reformat if it's a string
                    try:
                        # Try ISO format first
                        if len(booking['CheckInDate']) >= 10:
                            date_obj = datetime.strptime(booking['CheckInDate'][:10], '%Y-%m-%d')
                            booking['CheckInDate'] = date_obj.strftime('%Y-%m-%d')
                        else:
                            booking['CheckInDate'] = None
                    except:
                        try:
                            # Try parsing as datetime string
                            date_obj = datetime.fromisoformat(booking['CheckInDate'].replace('Z', '+00:00'))
                            booking['CheckInDate'] = date_obj.strftime('%Y-%m-%d')
                        except:
                            booking['CheckInDate'] = None
                else:
                    booking['CheckInDate'] = None
            else:
                booking['CheckInDate'] = None
                
            # Format CheckOutDate
            if booking['CheckOutDate']:
                if isinstance(booking['CheckOutDate'], (datetime, date)):
                    booking['CheckOutDate'] = booking['CheckOutDate'].strftime('%Y-%m-%d')
                elif isinstance(booking['CheckOutDate'], str) and booking['CheckOutDate'].strip() not in ('None', 'null', 'NULL', ''):
                    # Try to parse and reformat if it's a string
                    try:
                        # Try ISO format first
                        if len(booking['CheckOutDate']) >= 10:
                            date_obj = datetime.strptime(booking['CheckOutDate'][:10], '%Y-%m-%d')
                            booking['CheckOutDate'] = date_obj.strftime('%Y-%m-%d')
                        else:
                            booking['CheckOutDate'] = None
                    except:
                        try:
                            # Try parsing as datetime string
                            date_obj = datetime.fromisoformat(booking['CheckOutDate'].replace('Z', '+00:00'))
                            booking['CheckOutDate'] = date_obj.strftime('%Y-%m-%d')
                        except:
                            booking['CheckOutDate'] = None
                else:
                    booking['CheckOutDate'] = None
            else:
                booking['CheckOutDate'] = None
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'bookings': bookings})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/booking/cancel/<int:booking_id>', methods=['PUT'])
def cancel_booking(booking_id):
    """Cancel booking using STORED PROCEDURE (CancelBooking) - Triggers will execute automatically"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Call stored procedure
        # Note: AuditBookingStatusChange trigger will automatically log the status change
        args = [booking_id, '']  # BookingID, OUT: Message
        result = cursor.callproc('CancelBooking', args)
        
        message = result[1]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': 'successfully' in message.lower(),
            'message': message
        })
        
    except mysql.connector.Error as err:
        error_msg = str(err)
        # Handle trigger errors (like PreventOverbooking)
        if '45000' in error_msg or 'Hotel is not available' in error_msg:
            return jsonify({
                'success': False,
                'message': 'Hotel is not available for selected dates'
            }), 400
        return jsonify({'success': False, 'message': error_msg}), 400

# ============================================
# ROUTES - AUDIT LOGS & PAYMENT TRANSACTIONS (Trigger Results)
# ============================================

@app.route('/audit/bookings')
def get_booking_audit_logs():
    """Get booking audit logs created by AuditBookingStatusChange trigger"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            AuditID,
            BookingID,
            ActionType,
            OldStatus,
            NewStatus,
            ChangeDate,
            UserEmail
        FROM BookingAudit
        ORDER BY ChangeDate DESC
        LIMIT 100
        """
        cursor.execute(query)
        audit_logs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'auditLogs': audit_logs})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/audit/bookings/booking/<int:booking_id>')
def get_booking_audit_by_id(booking_id):
    """Get audit logs for a specific booking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            AuditID,
            BookingID,
            ActionType,
            OldStatus,
            NewStatus,
            ChangeDate,
            UserEmail
        FROM BookingAudit
        WHERE BookingID = %s
        ORDER BY ChangeDate DESC
        """
        cursor.execute(query, (booking_id,))
        audit_logs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'auditLogs': audit_logs})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/payments/transactions')
def get_payment_transactions():
    """Get payment transactions created by CreatePaymentOnBooking trigger"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            pt.TransactionID,
            pt.BookingID,
            pt.Amount,
            pt.PaymentStatus,
            pt.TransactionDate,
            b.UserID,
            h.Name AS HotelName
        FROM PaymentTransaction pt
        LEFT JOIN Booking b ON pt.BookingID = b.BookingID
        LEFT JOIN Hotel h ON b.HotelID = h.HotelID
        ORDER BY pt.TransactionDate DESC
        LIMIT 100
        """
        cursor.execute(query)
        transactions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'transactions': transactions})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/payments/transactions/booking/<int:booking_id>')
def get_payment_by_booking(booking_id):
    """Get payment transaction for a specific booking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            pt.TransactionID,
            pt.BookingID,
            pt.Amount,
            pt.PaymentStatus,
            pt.TransactionDate,
            b.UserID,
            h.Name AS HotelName
        FROM PaymentTransaction pt
        LEFT JOIN Booking b ON pt.BookingID = b.BookingID
        LEFT JOIN Hotel h ON b.HotelID = h.HotelID
        WHERE pt.BookingID = %s
        ORDER BY pt.TransactionDate DESC
        """
        cursor.execute(query, (booking_id,))
        transaction = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if transaction:
            return jsonify({'success': True, 'transaction': transaction})
        else:
            return jsonify({'success': False, 'message': 'Payment transaction not found'}), 404
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/payments/transactions/user/<int:user_id>')
def get_user_payments(user_id):
    """Get all payment transactions for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            pt.TransactionID,
            pt.BookingID,
            pt.Amount,
            pt.PaymentStatus,
            pt.TransactionDate,
            h.Name AS HotelName,
            b.CheckInDate,
            b.CheckOutDate
        FROM PaymentTransaction pt
        LEFT JOIN Booking b ON pt.BookingID = b.BookingID
        LEFT JOIN Hotel h ON b.HotelID = h.HotelID
        WHERE b.UserID = %s
        ORDER BY pt.TransactionDate DESC
        """
        cursor.execute(query, (user_id,))
        transactions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'transactions': transactions})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/payments/update-status/<int:transaction_id>', methods=['PUT'])
def update_payment_status(transaction_id):
    """Update payment transaction status"""
    try:
        data = request.json
        new_status = data.get('status', '').capitalize()
        
        # Validate status
        if new_status not in ['Pending', 'Completed', 'Failed']:
            return jsonify({
                'success': False,
                'message': 'Invalid status. Must be Pending, Completed, or Failed'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        UPDATE PaymentTransaction 
        SET PaymentStatus = %s 
        WHERE TransactionID = %s
        """
        cursor.execute(query, (new_status, transaction_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Payment status updated successfully'
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# ROUTES - DESTINATION MANAGEMENT
# ============================================

@app.route('/destinations')
def get_destinations():
    """Get all destinations (READ)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM Destination ORDER BY Name"
        cursor.execute(query)
        destinations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'destinations': destinations})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/destination/create', methods=['POST'])
def create_destination():
    """Create new destination (CREATE - Destination table)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO Destination (Name, Location, Type, Description, Rating)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['name'],
            data['location'],
            data['type'],
            data['description'],
            data['rating']
        ))
        
        conn.commit()
        dest_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Destination created successfully',
            'destId': dest_id
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/destination/delete/<int:dest_id>', methods=['DELETE'])
def delete_destination(dest_id):
    """Delete a destination and related itinerary references"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM Includes WHERE DestID = %s", (dest_id,))
        cursor.execute("DELETE FROM Destination WHERE DestID = %s", (dest_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Destination deleted successfully'})

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/destination/popularity/<int:dest_id>')
def check_destination_popularity(dest_id):
    """Check destination popularity using FUNCTION (IsDestinationPopular)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT IsDestinationPopular(%s) as popularity"
        cursor.execute(query, (dest_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'popularity': result[0]
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/destination/itineraries/<int:dest_id>')
def get_destination_itineraries(dest_id):
    """Get itineraries for destination using STORED PROCEDURE"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.callproc('GetDestinationItineraries', [dest_id])
        
        itineraries = []
        for result in cursor.stored_results():
            itineraries = result.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'itineraries': itineraries})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# ROUTES - ITINERARY MANAGEMENT
# ============================================

@app.route('/itinerary/create', methods=['POST'])
def create_itinerary():
    """Create new itinerary (CREATE - Itinerary + Includes tables)"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert itinerary
        query = """
        INSERT INTO Itinerary (UserID, Title, StartDate, EndDate, TotalCost)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['userId'],
            data['title'],
            data['startDate'],
            data['endDate'],
            data['totalCost']
        ))
        
        itinerary_id = cursor.lastrowid
        
        # Insert destinations into Includes table
        if 'destinations' in data and len(data['destinations']) > 0:
            includes_query = "INSERT INTO Includes (ItineraryID, DestID) VALUES (%s, %s)"
            for dest_id in data['destinations']:
                cursor.execute(includes_query, (itinerary_id, dest_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Itinerary created successfully',
            'itineraryId': itinerary_id
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/itineraries/user/<int:user_id>')
def get_user_itineraries(user_id):
    """Get all itineraries for a user (READ with JOIN)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            i.ItineraryID,
            i.Title,
            i.StartDate,
            i.EndDate,
            i.TotalCost,
            GROUP_CONCAT(d.Name SEPARATOR ', ') AS Destinations
        FROM Itinerary i
        LEFT JOIN Includes inc ON i.ItineraryID = inc.ItineraryID
        LEFT JOIN Destination d ON inc.DestID = d.DestID
        WHERE i.UserID = %s
        GROUP BY i.ItineraryID
        ORDER BY i.StartDate DESC
        """
        cursor.execute(query, (user_id,))
        itineraries = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'itineraries': itineraries})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/itinerary/delete/<int:itinerary_id>', methods=['DELETE'])
def delete_itinerary(itinerary_id):
    """Delete itinerary (DELETE - cascades to Includes)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM Itinerary WHERE ItineraryID = %s"
        cursor.execute(query, (itinerary_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Itinerary deleted successfully'
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# ROUTES - REPORTS & ANALYTICS
# ============================================

@app.route('/reports/user-spending/<int:user_id>')
def get_user_spending(user_id):
    """Get user total spending using FUNCTION (GetUserTotalSpending)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT GetUserTotalSpending(%s) as total_spending"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'totalSpending': float(result[0]) if result[0] else 0
        })
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/popular-destinations')
def get_popular_destinations():
    """Get all destinations with popularity status (Complex Query)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            d.DestID,
            d.Name,
            d.Location,
            d.Type,
            d.Rating,
            IsDestinationPopular(d.DestID) as PopularityStatus,
            COUNT(inc.ItineraryID) as TotalItineraries
        FROM Destination d
        LEFT JOIN Includes inc ON d.DestID = inc.DestID
        GROUP BY d.DestID
        ORDER BY TotalItineraries DESC
        """
        cursor.execute(query)
        destinations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'destinations': destinations})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/dashboard-stats')
def get_dashboard_stats():
    """Get dashboard statistics (Aggregate Queries)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        stats = {}
        
        # Total bookings
        cursor.execute("SELECT COUNT(*) as count FROM Booking")
        stats['totalBookings'] = cursor.fetchone()['count']
        
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM User")
        stats['totalUsers'] = cursor.fetchone()['count']
        
        # Total destinations
        cursor.execute("SELECT COUNT(*) as count FROM Destination")
        stats['totalDestinations'] = cursor.fetchone()['count']
        
        # Average hotel rating
        cursor.execute("SELECT AVG(Rating) as avg FROM Hotel")
        stats['avgHotelRating'] = round(cursor.fetchone()['avg'], 2)
        
        # Total revenue
        cursor.execute("SELECT SUM(TotalPrice) as total FROM Booking WHERE BookingStatus = 'Confirmed'")
        result = cursor.fetchone()
        stats['totalRevenue'] = float(result['total']) if result['total'] else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'stats': stats})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# ROUTES - ADVANCED QUERIES (Nested, Correlated)
# ============================================

@app.route('/reports/hotels-above-average-price')
def get_hotels_above_average_price():
    """Get hotels with price above average (NESTED QUERY - Subquery in WHERE clause)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # NESTED QUERY: Subquery in WHERE clause
        query = """
        SELECT 
            HotelID,
            Name,
            Location,
            PricePerNight,
            Rating
        FROM Hotel
        WHERE PricePerNight > (
            SELECT AVG(PricePerNight) 
            FROM Hotel
        )
        ORDER BY PricePerNight DESC
        """
        cursor.execute(query)
        hotels = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'hotels': hotels})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/users-with-bookings')
def get_users_with_bookings():
    """Get users who have made bookings (NESTED QUERY - Subquery with IN clause)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # NESTED QUERY: Subquery with IN clause
        query = """
        SELECT 
            UserID,
            FirstName,
            LastName,
            Email,
            PhoneNo
        FROM User
        WHERE UserID IN (
            SELECT DISTINCT UserID 
            FROM Booking 
            WHERE BookingStatus = 'Confirmed'
        )
        ORDER BY LastName, FirstName
        """
        cursor.execute(query)
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'users': users})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/destinations-not-in-itineraries')
def get_destinations_not_in_itineraries():
    """Get destinations that are not included in any itinerary (NESTED QUERY - Subquery with NOT IN)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # NESTED QUERY: Subquery with NOT IN clause
        query = """
        SELECT 
            DestID,
            Name,
            Location,
            Type,
            Rating
        FROM Destination
        WHERE DestID NOT IN (
            SELECT DISTINCT DestID 
            FROM Includes
            WHERE DestID IS NOT NULL
        )
        ORDER BY Name
        """
        cursor.execute(query)
        destinations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'destinations': destinations})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/bookings-with-hotel-details')
def get_bookings_with_hotel_details():
    """Get bookings with hotel details where hotel rating is above average (CORRELATED QUERY)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # CORRELATED QUERY: Subquery references outer query
        query = """
        SELECT 
            b.BookingID,
            b.CheckInDate,
            b.CheckOutDate,
            b.TotalPrice,
            b.BookingStatus,
            h.Name AS HotelName,
            h.Location AS HotelLocation,
            h.PricePerNight,
            h.Rating AS HotelRating,
            CONCAT(u.FirstName, ' ', u.LastName) AS UserName
        FROM Booking b
        INNER JOIN Hotel h ON b.HotelID = h.HotelID
        INNER JOIN User u ON b.UserID = u.UserID
        WHERE h.Rating > (
            SELECT AVG(Rating) 
            FROM Hotel h2 
            WHERE h2.Location = h.Location
        )
        ORDER BY b.BookingDate DESC
        """
        cursor.execute(query)
        bookings = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'bookings': bookings})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/users-booking-count')
def get_users_booking_count():
    """Get users with their booking counts (CORRELATED QUERY - Subquery in SELECT)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # CORRELATED QUERY: Subquery in SELECT clause that references outer query
        query = """
        SELECT 
            u.UserID,
            CONCAT(u.FirstName, ' ', u.LastName) AS UserName,
            u.Email,
            (
                SELECT COUNT(*) 
                FROM Booking b 
                WHERE b.UserID = u.UserID 
                AND b.BookingStatus = 'Confirmed'
            ) AS ConfirmedBookings,
            (
                SELECT COALESCE(SUM(b2.TotalPrice), 0)
                FROM Booking b2
                WHERE b2.UserID = u.UserID
                AND b2.BookingStatus = 'Confirmed'
            ) AS TotalSpending
        FROM User u
        ORDER BY ConfirmedBookings DESC, TotalSpending DESC
        """
        cursor.execute(query)
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'users': users})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

@app.route('/reports/hotels-booking-stats')
def get_hotels_booking_stats():
    """Get hotels with booking statistics using aggregate and join (AGGREGATE + JOIN QUERY)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # AGGREGATE + JOIN QUERY: Multiple aggregates with GROUP BY and JOINs
        query = """
        SELECT 
            h.HotelID,
            h.Name AS HotelName,
            h.Location,
            h.PricePerNight,
            h.Rating,
            COUNT(b.BookingID) AS TotalBookings,
            COUNT(CASE WHEN b.BookingStatus = 'Confirmed' THEN 1 END) AS ConfirmedBookings,
            COUNT(CASE WHEN b.BookingStatus = 'Cancelled' THEN 1 END) AS CancelledBookings,
            COALESCE(SUM(CASE WHEN b.BookingStatus = 'Confirmed' THEN b.TotalPrice ELSE 0 END), 0) AS TotalRevenue,
            COALESCE(AVG(CASE WHEN b.BookingStatus = 'Confirmed' THEN b.TotalPrice END), 0) AS AvgBookingValue
        FROM Hotel h
        LEFT JOIN Booking b ON h.HotelID = b.HotelID
        GROUP BY h.HotelID, h.Name, h.Location, h.PricePerNight, h.Rating
        HAVING TotalBookings > 0
        ORDER BY TotalRevenue DESC, ConfirmedBookings DESC
        """
        cursor.execute(query)
        hotels = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'hotels': hotels})
        
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)}), 400

# ============================================
# RUN THE APP
# ============================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)