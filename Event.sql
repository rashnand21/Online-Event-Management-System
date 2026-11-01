CREATE DATABASE IF NOT EXISTS event_management;
USE event_management;

-- 1. Admin
CREATE TABLE Admin (
    Admin_ID INT PRIMARY KEY AUTO_INCREMENT,
    Admin_Name VARCHAR(255) NOT NULL,
    Email VARCHAR(255),
    Password VARCHAR(8) NOT NULL,
    Phone_No VARCHAR(15)
);

-- 2. Organizer
CREATE TABLE Organizer (
    Organizer_ID INT PRIMARY KEY AUTO_INCREMENT,
    Organizer_Name VARCHAR(50) NOT NULL,
    Email VARCHAR(255),
    Phone_No VARCHAR(15),
    Organization_Name VARCHAR(50),
    Experience_Years DECIMAL(3,1),
    Password VARCHAR(8)
);

-- 3. User
CREATE TABLE `User` (
    User_ID INT PRIMARY KEY AUTO_INCREMENT,
    User_Name VARCHAR(50) NOT NULL,
    Phone_No VARCHAR(15),
    Address VARCHAR(255),
    Password VARCHAR(8)
);

-- 4. Hall
CREATE TABLE Hall (
    Hall_ID INT PRIMARY KEY AUTO_INCREMENT,
    Hall_Name VARCHAR(50),
    Location VARCHAR(100),
    Capacity INT,
    Hall_Charges DECIMAL(10,2),
    Available_From DATE,
    Available_To DATE,
    Availability_Status VARCHAR(10) CHECK (Availability_Status IN ('Available', 'Booked'))
);

-- 5. Service
CREATE TABLE Service (
    Service_ID INT PRIMARY KEY AUTO_INCREMENT,
    Service_Name VARCHAR(100) NOT NULL,
    Service_Cost DECIMAL(10,2),
    Service_Type VARCHAR(50),
    Is_Free VARCHAR(10)
);

-- 6. Event
CREATE TABLE `Event` (
    Event_ID INT PRIMARY KEY AUTO_INCREMENT,
    Event_Name VARCHAR(50) NOT NULL,
    Event_Type VARCHAR(30) NOT NULL,
    Location VARCHAR(50),
    Booking_Before_Date DATE,
    Actual_Event_Date DATE,
    Max_Capacity INT,
    Organizer_ID INT,
    Status VARCHAR(10) CHECK (Status IN ('Upcoming', 'Completed', 'Cancelled')),
    FOREIGN KEY (Organizer_ID) REFERENCES Organizer(Organizer_ID)
);

-- 7. Packages
CREATE TABLE Packages (
    Package_ID INT PRIMARY KEY AUTO_INCREMENT,
    Package_Name VARCHAR(100),
    Package_Cost DECIMAL(10,2),
    Max_Attendees INT,
    Include_Free_Service VARCHAR(10),
    Event_ID INT,
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID)
);



-- 8. Offer_Discount
CREATE TABLE Offer_Discount (
    Offer_ID INT PRIMARY KEY AUTO_INCREMENT,
    Offer_Code VARCHAR(20),
    Discount_Per DECIMAL(5,2),
    Valid_From DATE,
    Valid_To DATE,
    Package_ID INT,
    Event_ID INT,
    FOREIGN KEY (Package_ID) REFERENCES Packages(Package_ID),
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID)
);

-- 9. Schedule
CREATE TABLE Schedule (
    Schedule_ID INT PRIMARY KEY AUTO_INCREMENT,
    Event_ID INT,
    Activity_Name VARCHAR(50),
    Start_Time TIME,
    End_Time TIME,
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID)
);

-- 10. Staff
CREATE TABLE Staff (
    Staff_ID INT PRIMARY KEY AUTO_INCREMENT,
    Staff_Name VARCHAR(50) NOT NULL,
    Role VARCHAR(20) NOT NULL,
    Contact_No VARCHAR(15),
    Availability_Status VARCHAR(10),
    Event_ID INT,
    Organizer_ID INT,
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID),
    FOREIGN KEY (Organizer_ID) REFERENCES Organizer(Organizer_ID)
);

-- 11. Booking
CREATE TABLE Booking (
    Booking_ID INT PRIMARY KEY AUTO_INCREMENT,
    Booking_Date DATE,
    Seats_Booked INT NOT NULL,
    Total_Amt DECIMAL(10,2) NOT NULL,
    User_ID INT,
    Event_ID INT,
    Hall_ID INT,
    FOREIGN KEY (User_ID) REFERENCES `User`(User_ID),
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID),
    FOREIGN KEY (Hall_ID) REFERENCES Hall(Hall_ID)
);

-- 12. Hall_Slot
CREATE TABLE Hall_Slot (
    Slot_ID INT PRIMARY KEY AUTO_INCREMENT,
    Date DATE,
    Hall_ID INT,
    Start_Time TIME,
    End_Time TIME,
    Booking_ID INT,
    FOREIGN KEY (Hall_ID) REFERENCES Hall(Hall_ID),
    FOREIGN KEY (Booking_ID) REFERENCES Booking(Booking_ID)
);

-- 13. Payment
CREATE TABLE Payment (
    Payment_ID INT PRIMARY KEY AUTO_INCREMENT,
    Booking_ID INT,
    Payment_Mode VARCHAR(15),
    Payment_Date DATE,
    Payment_Status VARCHAR(20),
    Amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (Booking_ID) REFERENCES Booking(Booking_ID)
);

-- 14. Feedback
CREATE TABLE Feedback (
    Feedback_ID INT PRIMARY KEY AUTO_INCREMENT,
    Comments TEXT,
    User_ID INT,
    Rating INT CHECK (Rating BETWEEN 1 AND 5),
    Event_ID INT,
    FOREIGN KEY (User_ID) REFERENCES `User`(User_ID),
    FOREIGN KEY (Event_ID) REFERENCES `Event`(Event_ID)
);



USE event_management;

-- 1. Admin
INSERT INTO Admin (Admin_ID, Admin_Name, Email, Password, Phone_No) VALUES
(1, 'Tejal Admin', 'admin@events.com', 'admin123', '9876500001'),
(2, 'Rohan Patil', 'rohan@events.com', 'admin456', '9876500002');

-- 2. Organizer
INSERT INTO Organizer (Organizer_ID, Organizer_Name, Email, Phone_No, Organization_Name, Experience_Years, Password) VALUES
(1, 'Amit Deshmukh', 'amit@eventpro.com', '9823011111', 'EventPro Nashik', 5.5, 'amit1234'),
(2, 'Sneha Kulkarni', 'sneha@dreamevents.com', '9823022222', 'Dream Events', 3.0, 'sneha123'),
(3, 'Rahul Jadhav', 'rahul@startuphub.com', '9823033333', 'Startup Hub', 7.5, 'rahul123');

-- 3. User
INSERT INTO `User` (User_ID, User_Name, Phone_No, Address, Password) VALUES
(1, 'Priya Sharma', '9911001111', 'College Road, Nashik', 'priya123'),
(2, 'Karan Mehta', '9911002222', 'Gangapur Road, Nashik', 'karan123'),
(3, 'Neha Joshi', '9911003333', 'Panchavati, Nashik', 'neha1234'),
(4, 'Vikas Pawar', '9911004444', 'Nashik Road, Nashik', 'vikas123'),
(5, 'Anjali More', '9911005555', 'Satpur, Nashik', 'anjali12');

-- 4. Hall
INSERT INTO Hall (Hall_ID, Hall_Name, Location, Capacity, Hall_Charges, Available_From, Available_To, Availability_Status) VALUES
(1, 'Grand Hall', 'College Road, Nashik', 300, 25000.00, '2026-10-01', '2027-03-31', 'Available'),
(2, 'Royal Palace', 'Gangapur Road, Nashik', 500, 40000.00, '2026-10-01', '2027-03-31', 'Available'),
(3, 'Sky Arena', 'Baner, Pune', 800, 60000.00, '2026-10-01', '2027-03-31', 'Available'),
(4, 'Green Lawn', 'Panchavati, Nashik', 200, 15000.00, '2026-08-01', '2026-12-31', 'Booked');

-- 5. Service
INSERT INTO Service (Service_ID, Service_Name, Service_Cost, Service_Type, Is_Free) VALUES
(1, 'Catering', 15000.00, 'Food', 'No'),
(2, 'Stage Decoration', 10000.00, 'Decoration', 'No'),
(3, 'Sound and Lighting', 12000.00, 'Technical', 'No'),
(4, 'Photography', 8000.00, 'Media', 'No'),
(5, 'Parking', 0.00, 'Facility', 'Yes');

-- 6. Event
INSERT INTO `Event` (Event_ID, Event_Name, Event_Type, Location, Booking_Before_Date, Actual_Event_Date, Max_Capacity, Organizer_ID, Status) VALUES
(1, 'Tech Summit 2026', 'Conference', 'Nashik', '2026-11-20', '2026-12-01', 200, 1, 'Upcoming'),
(2, 'Wedding Expo', 'Exhibition', 'Nashik', '2026-11-10', '2026-11-15', 300, 2, 'Upcoming'),
(3, 'Music Night', 'Concert', 'Pune', '2026-12-05', '2026-12-12', 500, 1, 'Upcoming'),
(4, 'Startup Meet', 'Seminar', 'Mumbai', '2026-08-20', '2026-08-25', 100, 3, 'Completed'),
(5, 'Food Festival', 'Festival', 'Nashik', '2026-12-15', '2026-12-22', 400, 2, 'Upcoming');

-- 7. Packages
INSERT INTO Packages (Package_ID, Package_Name, Package_Cost, Max_Attendees, Include_Free_Service, Event_ID) VALUES
(1, 'Silver Pass', 500.00, 5, 'No', 1),
(2, 'Gold Pass', 1200.00, 10, 'Yes', 1),
(3, 'Standard Entry', 300.00, 5, 'No', 2),
(4, 'VIP Pass', 2000.00, 4, 'Yes', 3),
(5, 'Basic Entry', 250.00, 6, 'No', 5);

-- 8. Offer_Discount
INSERT INTO Offer_Discount (Offer_ID, Offer_Code, Discount_Per, Valid_From, Valid_To, Package_ID, Event_ID) VALUES
(1, 'TECH10', 10.00, '2026-09-01', '2026-11-30', 1, 1),
(2, 'EXPO15', 15.00, '2026-09-01', '2026-11-10', 3, 2),
(3, 'MUSIC20', 20.00, '2026-09-01', '2026-12-05', 4, 3);

-- 9. Schedule
INSERT INTO Schedule (Schedule_ID, Event_ID, Activity_Name, Start_Time, End_Time) VALUES
(1, 1, 'Registration', '09:00:00', '10:00:00'),
(2, 1, 'Keynote Speech', '10:00:00', '11:30:00'),
(3, 1, 'Panel Discussion', '12:00:00', '14:00:00'),
(4, 2, 'Exhibition Opening', '10:00:00', '11:00:00'),
(5, 3, 'Live Performance', '19:00:00', '22:00:00'),
(6, 5, 'Food Stalls Open', '11:00:00', '21:00:00');

-- 10. Staff
INSERT INTO Staff (Staff_ID, Staff_Name, Role, Contact_No, Availability_Status, Event_ID, Organizer_ID) VALUES
(1, 'Suresh Gaikwad', 'Coordinator', '9700011111', 'Available', 1, 1),
(2, 'Pooja Nikam', 'Registration', '9700022222', 'Available', 1, 1),
(3, 'Manoj Shinde', 'Security', '9700033333', 'Busy', 2, 2),
(4, 'Kavita Rane', 'Anchor', '9700044444', 'Available', 3, 1),
(5, 'Deepak Thakur', 'Technician', '9700055555', 'Available', 5, 2);

-- 11. Booking
INSERT INTO Booking (Booking_ID, Booking_Date, Seats_Booked, Total_Amt, User_ID, Event_ID, Hall_ID) VALUES
(1, '2026-09-20', 2, 1000.00, 1, 1, 1),
(2, '2026-09-22', 3, 900.00, 2, 2, 2),
(3, '2026-09-25', 2, 3200.00, 3, 3, 3),
(4, '2026-08-10', 1, 500.00, 4, 4, 4);

-- 12. Hall_Slot
INSERT INTO Hall_Slot (Slot_ID, Date, Hall_ID, Start_Time, End_Time, Booking_ID) VALUES
(1, '2026-12-01', 1, '09:00:00', '18:00:00', 1),
(2, '2026-11-15', 2, '09:00:00', '18:00:00', 2),
(3, '2026-12-12', 3, '17:00:00', '23:00:00', 3),
(4, '2026-08-25', 4, '09:00:00', '18:00:00', 4);

-- 13. Payment
INSERT INTO Payment (Payment_ID, Booking_ID, Payment_Mode, Payment_Date, Payment_Status, Amount) VALUES
(1, 1, 'UPI', '2026-09-20', 'Paid', 1000.00),
(2, 2, 'Card', '2026-09-22', 'Paid', 900.00),
(3, 3, 'UPI', '2026-09-25', 'Paid', 3200.00),
(4, 4, 'Cash', '2026-08-10', 'Paid', 500.00);

-- 14. Feedback
INSERT INTO Feedback (Feedback_ID, Comments, User_ID, Rating, Event_ID) VALUES
(1, 'Very well organized event.', 4, 5, 4),
(2, 'Good speakers, nice venue.', 1, 4, 4),
(3, 'Could have started on time.', 2, 3, 4);





select * from user;
USE event_management;
ALTER TABLE `Event` ADD COLUMN Event_Time TIME NULL AFTER Actual_Event_Date;
UPDATE `Event` SET Event_Time = '10:00:00' WHERE Event_ID > 0;