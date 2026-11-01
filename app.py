import os
from datetime import date
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, abort)
from dotenv import load_dotenv
from db import get_connection

# Load private settings from the local .env file.
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. Add it to your local .env file."
    )


# ---------- helpers ----------
def query(sql, args=(), one=False, commit=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, args)
    if commit:
        conn.commit()
        result = cur.lastrowid
    else:
        rows = cur.fetchall()
        result = (rows[0] if rows else None) if one else rows
    cur.close()
    conn.close()
    return result


def val(sql, args=()):
    """Return the first value of the first row (for COUNT, SUM, AVG)."""
    return list(query(sql, args, one=True).values())[0]


def form(*names):
    return tuple(request.form.get(n) for n in names)


def role(name):
    """Allow a page only for one role."""
    def deco(f):
        @wraps(f)
        def inner(*a, **k):
            if session.get("role") != name:
                flash("Please log in as %s." % name, "warning")
                return redirect(url_for("login"))
            return f(*a, **k)
        return inner
    return deco


def get_event(event_id):
    return query("""SELECT e.*, o.Organizer_Name, o.Organization_Name FROM `Event` e
                    LEFT JOIN Organizer o ON o.Organizer_ID=e.Organizer_ID
                    WHERE e.Event_ID=%s""", (event_id,), one=True)


NOT_REFUNDED = "COALESCE(p.Payment_Status,'')<>'Refunded'"
BOOKED = ("(SELECT COALESCE(SUM(b.Seats_Booked),0) FROM Booking b "
          "LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID "
          "WHERE b.Event_ID=e.Event_ID AND " + NOT_REFUNDED + ")")


def seats_left(e):
    booked = val("SELECT COALESCE(SUM(b.Seats_Booked),0) FROM Booking b "
                 "LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID "
                 "WHERE b.Event_ID=%s AND " + NOT_REFUNDED, (e["Event_ID"],))
    return e["Max_Capacity"] - int(booked)


def cancel_event(event_id):
    query("UPDATE `Event` SET Status='Cancelled' WHERE Event_ID=%s", (event_id,), commit=True)
    query("""UPDATE Payment p JOIN Booking b ON b.Booking_ID=p.Booking_ID
             SET p.Payment_Status='Refunded' WHERE b.Event_ID=%s""", (event_id,), commit=True)


def action_route(name, param, who, sql, back, owner=False):
    """Makes a small POST route that runs one SQL statement and goes back."""
    def view(**kw):
        args = list(kw.values()) + ([session["id"]] if owner else [])
        try:
            query(sql, args, commit=True)
            flash("Done.", "success")
        except Exception:
            flash("This item is in use and cannot be deleted.", "warning")
        return redirect(url_for(back))
    app.add_url_rule("/%s/<int:%s>" % (name, param), name, role(who)(view), methods=["POST"])


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------- public ----------
@app.route("/")
def index():
    stats = {"events": val("SELECT COUNT(*) FROM `Event`"),
             "bookings": val("SELECT COUNT(*) FROM Booking"),
             "users": val("SELECT COUNT(*) FROM `User`"),
             "rating": val("SELECT ROUND(AVG(Rating),1) FROM Feedback") or 0}
    return render_template(
        "index.html", stats=stats,
        events=query("SELECT * FROM `Event` WHERE Status='Upcoming' "
                     "ORDER BY Actual_Event_Date LIMIT 3"),
        services=query("SELECT * FROM Service LIMIT 8"),
        feedbacks=query("""SELECT u.User_Name, e.Event_Name, f.Rating, f.Comments
                           FROM Feedback f JOIN `User` u ON u.User_ID=f.User_ID
                           JOIN `Event` e ON e.Event_ID=f.Event_ID
                           ORDER BY f.Feedback_ID DESC LIMIT 3"""))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/events")
def events():
    q = request.args.get("q", "").strip()
    etype = request.args.get("type", "")
    status = request.args.get("status", "")
    sql = "SELECT * FROM `Event` WHERE (Event_Name LIKE %s OR Location LIKE %s)"
    args = ["%" + q + "%"] * 2
    if etype:
        sql += " AND Event_Type=%s"
        args.append(etype)
    if status:
        sql += " AND Status=%s"
        args.append(status)
    types = [r["Event_Type"] for r in query("SELECT DISTINCT Event_Type FROM `Event`")]
    return render_template("events.html", q=q, event_types=types,
                           selected_type=etype, selected_status=status,
                           events=query(sql + " ORDER BY Actual_Event_Date", args))


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = get_event(event_id)
    if not event:
        abort(404)
    return render_template(
        "event_detail.html", event=event, seats_left=seats_left(event),
        schedule=query("SELECT * FROM Schedule WHERE Event_ID=%s ORDER BY Start_Time", (event_id,)),
        packages=query("SELECT * FROM Packages WHERE Event_ID=%s", (event_id,)),
        offers=query("SELECT * FROM Offer_Discount WHERE Event_ID=%s AND Valid_To>=CURDATE()",
                     (event_id,)),
        feedbacks=query("""SELECT u.User_Name, f.Rating, f.Comments FROM Feedback f
                           JOIN `User` u ON u.User_ID=f.User_ID WHERE f.Event_ID=%s""",
                        (event_id,)))


# ---------- login / register ----------
ROLES = {"admin": ("Admin", "Admin_ID", "Admin_Name"),
         "organizer": ("Organizer", "Organizer_ID", "Organizer_Name"),
         "user": ("`User`", "User_ID", "User_Name")}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        who, uid, pw = form("role", "user_id", "password")
        if who in ROLES:
            table, idc, namec = ROLES[who]
            row = query("SELECT %s AS id, %s AS name FROM %s WHERE %s=%%s AND Password=%%s"
                        % (idc, namec, table, idc), (uid, pw), one=True)
            if row:
                session["role"], session["id"], session["name"] = who, row["id"], row["name"]
                flash("Welcome, %s!" % row["name"], "success")
                return redirect(url_for("dashboard"))
        flash("Wrong ID or password.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        who, name, phone, pw = form("role", "name", "phone", "password")
        if not name or not phone.isdigit() or len(phone) != 10 or not 1 <= len(pw) <= 8:
            flash("Enter a name, a 10 digit phone and a password of up to 8 characters.", "danger")
            return redirect(url_for("register"))
        if who == "organizer":
            new_id = query("""INSERT INTO Organizer (Organizer_Name, Phone_No, Password, Email,
                              Organization_Name, Experience_Years) VALUES (%s,%s,%s,%s,%s,%s)""",
                           (name, phone, pw) + form("email", "organization") +
                           (request.form.get("experience") or 0,), commit=True)
        else:
            who = "user"
            new_id = query("INSERT INTO `User` (User_Name, Phone_No, Password, Address) "
                           "VALUES (%s,%s,%s,%s)",
                           (name, phone, pw, request.form.get("address")), commit=True)
        flash("Registered. Your %s ID is %s. Use it to log in." % (who, new_id), "success")
        return redirect(url_for("login", role=who))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- dashboard ----------
@app.route("/dashboard")
def dashboard():
    who, uid = session.get("role"), session.get("id")
    if not who:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    if who == "user":
        stats = {
            "total_bookings": val("SELECT COUNT(*) FROM Booking WHERE User_ID=%s", (uid,)),
            "upcoming": val("""SELECT COUNT(*) FROM Booking b JOIN `Event` e ON e.Event_ID=b.Event_ID
                               WHERE b.User_ID=%s AND e.Status='Upcoming'""", (uid,)),
            "total_spent": val("""SELECT COALESCE(SUM(p.Amount),0) FROM Payment p
                                  JOIN Booking b ON b.Booking_ID=p.Booking_ID
                                  WHERE b.User_ID=%s AND p.Payment_Status='Paid'""", (uid,))}
        recent = query("""SELECT b.Booking_ID, e.Event_Name, e.Actual_Event_Date, b.Seats_Booked,
                                 b.Total_Amt, p.Payment_Status
                          FROM Booking b JOIN `Event` e ON e.Event_ID=b.Event_ID
                          LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID
                          WHERE b.User_ID=%s ORDER BY b.Booking_ID DESC LIMIT 5""", (uid,))
        upcoming = query("SELECT * FROM `Event` WHERE Status='Upcoming' "
                         "ORDER BY Actual_Event_Date LIMIT 3")
        return render_template("user_dashboard.html", stats=stats,
                               recent_bookings=recent, upcoming_events=upcoming)

    if who == "organizer":
        evs = query("SELECT e.*, " + BOOKED + " AS Booked_Seats FROM `Event` e "
                    "WHERE e.Organizer_ID=%s ORDER BY e.Actual_Event_Date DESC", (uid,))
        bookings = query("""SELECT b.Booking_ID, e.Event_Name, u.User_Name, u.Phone_No,
                                   b.Booking_Date, b.Seats_Booked, b.Total_Amt, p.Payment_Status
                            FROM Booking b JOIN `Event` e ON e.Event_ID=b.Event_ID
                            JOIN `User` u ON u.User_ID=b.User_ID
                            LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID
                            WHERE e.Organizer_ID=%s ORDER BY b.Booking_ID DESC""", (uid,))
        staff = query("""SELECT s.*, e.Event_Name FROM Staff s
                         LEFT JOIN `Event` e ON e.Event_ID=s.Event_ID
                         WHERE s.Organizer_ID=%s""", (uid,))
        revenue = val("""SELECT COALESCE(SUM(p.Amount),0) FROM Payment p
                         JOIN Booking b ON b.Booking_ID=p.Booking_ID
                         JOIN `Event` e ON e.Event_ID=b.Event_ID
                         WHERE e.Organizer_ID=%s AND p.Payment_Status='Paid'""", (uid,))
        stats = {"total_events": len(evs), "total_bookings": len(bookings),
                 "revenue": revenue, "total_staff": len(staff)}
        return render_template("organizer_dashboard.html", stats=stats,
                               events=evs, bookings=bookings, staff=staff)

    stats = {"events": val("SELECT COUNT(*) FROM `Event`"),
             "bookings": val("SELECT COUNT(*) FROM Booking"),
             "users": val("SELECT COUNT(*) FROM `User`"),
             "organizers": val("SELECT COUNT(*) FROM Organizer"),
             "halls": val("SELECT COUNT(*) FROM Hall"),
             "services": val("SELECT COUNT(*) FROM Service"),
             "revenue": val("SELECT COALESCE(SUM(Amount),0) FROM Payment WHERE Payment_Status='Paid'"),
             "rating": val("SELECT ROUND(AVG(Rating),1) FROM Feedback") or 0}
    return render_template(
        "admin_dashboard.html", stats=stats,
        recent_bookings=query("""SELECT b.Booking_ID, u.User_Name, e.Event_Name, b.Booking_Date,
                                        b.Seats_Booked, b.Total_Amt
                                 FROM Booking b JOIN `User` u ON u.User_ID=b.User_ID
                                 JOIN `Event` e ON e.Event_ID=b.Event_ID
                                 ORDER BY b.Booking_ID DESC LIMIT 5"""),
        recent_feedback=query("""SELECT u.User_Name, e.Event_Name, f.Rating, f.Comments
                                 FROM Feedback f JOIN `User` u ON u.User_ID=f.User_ID
                                 JOIN `Event` e ON e.Event_ID=f.Event_ID
                                 ORDER BY f.Feedback_ID DESC LIMIT 5"""))


# ---------- user: booking, payment, feedback ----------
@app.route("/events/<int:event_id>/book", methods=["GET", "POST"])
@role("user")
def book_event(event_id):
    event = get_event(event_id)
    if not event:
        abort(404)
    left = seats_left(event)
    if (event["Status"] != "Upcoming" or left <= 0
            or date.today() > event["Booking_Before_Date"]):
        flash("This event is closed for booking or sold out.", "warning")
        return redirect(url_for("event_detail", event_id=event_id))

    if request.method == "POST":
        package_id, hall_id, mode = form("package_id", "hall_id", "payment_mode")
        seats = int(request.form.get("seats") or 0)
        package = query("SELECT * FROM Packages WHERE Package_ID=%s AND Event_ID=%s",
                        (package_id, event_id), one=True)
        hall = query("SELECT Hall_ID FROM Hall WHERE Hall_ID=%s AND Availability_Status='Available'",
                     (hall_id,), one=True)
        back = redirect(url_for("book_event", event_id=event_id))

        if not package or not hall or mode not in ("UPI", "Card", "Cash"):
            flash("Choose a valid package, hall and payment mode.", "danger")
            return back
        if not 1 <= seats <= min(left, package["Max_Attendees"]):
            flash("Seats must be between 1 and %s." % min(left, package["Max_Attendees"]), "danger")
            return back

        discount = 0
        code = request.form.get("offer_code", "").strip().upper()
        if code:
            offer = query("""SELECT Discount_Per FROM Offer_Discount WHERE Offer_Code=%s
                             AND Package_ID=%s AND CURDATE() BETWEEN Valid_From AND Valid_To""",
                          (code, package_id), one=True)
            if not offer:
                flash("Invalid or expired offer code.", "danger")
                return back
            discount = float(offer["Discount_Per"])

        total = round(float(package["Package_Cost"]) * seats * (100 - discount) / 100, 2)
        booking_id = query("""INSERT INTO Booking (Booking_Date, Seats_Booked, Total_Amt,
                              User_ID, Event_ID, Hall_ID) VALUES (%s,%s,%s,%s,%s,%s)""",
                           (date.today(), seats, total, session["id"], event_id, hall_id),
                           commit=True)
        query("INSERT INTO Hall_Slot (`Date`, Hall_ID, Start_Time, End_Time, Booking_ID) "
              "VALUES (%s,%s,'09:00:00','18:00:00',%s)",
              (event["Actual_Event_Date"], hall_id, booking_id), commit=True)
        query("INSERT INTO Payment (Booking_ID, Payment_Mode, Payment_Date, Payment_Status, Amount) "
              "VALUES (%s,%s,%s,'Paid',%s)", (booking_id, mode, date.today(), total), commit=True)
        flash("Booking confirmed!", "success")
        return redirect(url_for("payment_success", booking_id=booking_id))

    return render_template(
        "book_event.html", event=event, seats_left=left,
        packages=query("SELECT * FROM Packages WHERE Event_ID=%s", (event_id,)),
        halls=query("SELECT * FROM Hall WHERE Availability_Status='Available'"),
        offers=query("SELECT * FROM Offer_Discount WHERE Event_ID=%s AND Valid_To>=CURDATE()",
                     (event_id,)))


@app.route("/payment/<int:booking_id>")
@role("user")
def payment_success(booking_id):
    receipt = query("""SELECT u.User_Name, b.Booking_ID, b.Booking_Date, e.Event_Name,
                              e.Actual_Event_Date, e.Location, h.Hall_Name, b.Seats_Booked,
                              p.Payment_ID, p.Payment_Mode, p.Payment_Status, p.Amount
                       FROM Booking b JOIN `User` u ON u.User_ID=b.User_ID
                       JOIN `Event` e ON e.Event_ID=b.Event_ID
                       LEFT JOIN Hall h ON h.Hall_ID=b.Hall_ID
                       JOIN Payment p ON p.Booking_ID=b.Booking_ID
                       WHERE b.Booking_ID=%s AND b.User_ID=%s""",
                    (booking_id, session["id"]), one=True)
    if not receipt:
        abort(404)
    return render_template("payment.html", receipt=receipt)


@app.route("/my-bookings")
@role("user")
def my_bookings():
    return render_template("my_bookings.html", bookings=query(
        """SELECT b.Booking_ID, b.Event_ID, e.Event_Name, e.Actual_Event_Date, h.Hall_Name,
                  b.Seats_Booked, b.Total_Amt, p.Payment_Status, p.Payment_Mode, e.Status
           FROM Booking b JOIN `Event` e ON e.Event_ID=b.Event_ID
           LEFT JOIN Hall h ON h.Hall_ID=b.Hall_ID
           LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID
           WHERE b.User_ID=%s ORDER BY b.Booking_ID DESC""", (session["id"],)))


@app.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role("user")
def cancel_booking(booking_id):
    if query("SELECT 1 FROM Booking WHERE Booking_ID=%s AND User_ID=%s",
             (booking_id, session["id"]), one=True):
        query("UPDATE Payment SET Payment_Status='Refunded' WHERE Booking_ID=%s",
              (booking_id,), commit=True)
        query("DELETE FROM Hall_Slot WHERE Booking_ID=%s", (booking_id,), commit=True)
        flash("Booking cancelled. Payment marked as refunded.", "success")
    return redirect(url_for("my_bookings"))


@app.route("/feedback", methods=["GET", "POST"])
@role("user")
def feedback():
    uid = session["id"]
    if request.method == "POST":
        event_id, comments = form("event_id", "comments")
        rating = int(request.form.get("rating") or 0)
        if 1 <= rating <= 5 and comments:
            query("INSERT INTO Feedback (Comments, User_ID, Rating, Event_ID) VALUES (%s,%s,%s,%s)",
                  (comments, uid, rating, event_id), commit=True)
            flash("Thank you for your feedback!", "success")
        return redirect(url_for("feedback"))
    # completed events this user booked and has not reviewed yet
    evs = query("""SELECT DISTINCT e.Event_ID, e.Event_Name, e.Actual_Event_Date
                   FROM `Event` e JOIN Booking b ON b.Event_ID=e.Event_ID
                   WHERE b.User_ID=%s AND e.Status='Completed' AND e.Event_ID NOT IN
                         (SELECT Event_ID FROM Feedback WHERE User_ID=%s)""", (uid, uid))
    mine = query("""SELECT f.*, e.Event_Name FROM Feedback f JOIN `Event` e ON e.Event_ID=f.Event_ID
                    WHERE f.User_ID=%s ORDER BY f.Feedback_ID DESC""", (uid,))
    return render_template("feedback.html", events=evs, my_feedbacks=mine,
                           selected_event=request.args.get("event_id", type=int))


# ---------- organizer ----------
def my_events(upcoming=False):
    return query("SELECT * FROM `Event` WHERE Organizer_ID=%s" +
                 (" AND Status='Upcoming'" if upcoming else ""), (session["id"],))


def is_mine(event_id):
    return query("SELECT 1 FROM `Event` WHERE Event_ID=%s AND Organizer_ID=%s",
                 (event_id, session["id"]), one=True)


@app.route("/organizer/create-event", methods=["GET", "POST"])
@role("organizer")
def create_event():
    if request.method == "POST":
        name, etype, loc, cap, before, edate = form(
            "event_name", "event_type", "location", "max_capacity", "booking_before", "event_date")
        if before > edate:
            flash("Booking must close on or before the event date.", "danger")
            return redirect(url_for("create_event"))
        query("""INSERT INTO `Event` (Event_Name, Event_Type, Location, Max_Capacity,
                 Booking_Before_Date, Actual_Event_Date, Organizer_ID, Status)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,'Upcoming')""",
              (name, etype, loc, cap, before, edate, session["id"]), commit=True)
        flash("Event created.", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_event.html")


@app.route("/organizer/schedule", methods=["GET", "POST"])
@role("organizer")
def add_schedule():
    if request.method == "POST":
        event_id = request.form.get("event_id")
        if is_mine(event_id):
            query("INSERT INTO Schedule (Event_ID, Activity_Name, Start_Time, End_Time) "
                  "VALUES (%s,%s,%s,%s)",
                  (event_id,) + form("activity_name", "start_time", "end_time"), commit=True)
            flash("Activity added.", "success")
        return redirect(url_for("add_schedule"))
    return render_template("add_schedule.html", events=my_events(True), schedules=query(
        """SELECT s.*, e.Event_Name FROM Schedule s JOIN `Event` e ON e.Event_ID=s.Event_ID
           WHERE e.Organizer_ID=%s ORDER BY e.Event_ID, s.Start_Time""", (session["id"],)))


@app.route("/organizer/package", methods=["GET", "POST"])
@role("organizer")
def add_package():
    if request.method == "POST":
        event_id = request.form.get("event_id")
        if is_mine(event_id):
            query("""INSERT INTO Packages (Package_Name, Package_Cost, Max_Attendees,
                     Include_Free_Service, Event_ID) VALUES (%s,%s,%s,%s,%s)""",
                  form("package_name", "package_cost", "max_attendees", "free_service") +
                  (event_id,), commit=True)
            flash("Package added.", "success")
        return redirect(url_for("add_package"))
    return render_template("add_package.html", events=my_events(True), packages=query(
        """SELECT p.*, e.Event_Name FROM Packages p JOIN `Event` e ON e.Event_ID=p.Event_ID
           WHERE e.Organizer_ID=%s""", (session["id"],)))


@app.route("/organizer/offer", methods=["GET", "POST"])
@role("organizer")
def add_offer():
    if request.method == "POST":
        pkg = query("""SELECT p.Package_ID, p.Event_ID FROM Packages p
                       JOIN `Event` e ON e.Event_ID=p.Event_ID
                       WHERE p.Package_ID=%s AND e.Organizer_ID=%s""",
                    (request.form.get("package_id"), session["id"]), one=True)
        if pkg:
            code, disc, vfrom, vto = form("offer_code", "discount", "valid_from", "valid_to")
            query("""INSERT INTO Offer_Discount (Offer_Code, Discount_Per, Valid_From, Valid_To,
                     Package_ID, Event_ID) VALUES (%s,%s,%s,%s,%s,%s)""",
                  (code.upper(), disc, vfrom, vto, pkg["Package_ID"], pkg["Event_ID"]), commit=True)
            flash("Offer added.", "success")
        return redirect(url_for("add_offer"))
    uid = (session["id"],)
    return render_template(
        "add_offer.html",
        packages=query("""SELECT p.Package_ID, p.Package_Name, e.Event_Name FROM Packages p
                          JOIN `Event` e ON e.Event_ID=p.Event_ID
                          WHERE e.Organizer_ID=%s AND e.Status='Upcoming'""", uid),
        offers=query("""SELECT o.*, e.Event_Name, p.Package_Name FROM Offer_Discount o
                        JOIN `Event` e ON e.Event_ID=o.Event_ID
                        LEFT JOIN Packages p ON p.Package_ID=o.Package_ID
                        WHERE e.Organizer_ID=%s""", uid))


@app.route("/organizer/staff", methods=["GET", "POST"])
@role("organizer")
def add_staff():
    if request.method == "POST":
        event_id = request.form.get("event_id")
        if is_mine(event_id):
            query("""INSERT INTO Staff (Staff_Name, Role, Contact_No, Availability_Status,
                     Event_ID, Organizer_ID) VALUES (%s,%s,%s,%s,%s,%s)""",
                  form("staff_name", "role", "contact_no", "availability") +
                  (event_id, session["id"]), commit=True)
            flash("Staff member added.", "success")
        return redirect(url_for("add_staff"))
    return render_template("add_staff.html", events=my_events(True), staff=query(
        """SELECT s.*, e.Event_Name FROM Staff s LEFT JOIN `Event` e ON e.Event_ID=s.Event_ID
           WHERE s.Organizer_ID=%s""", (session["id"],)))


@app.route("/organizer/event/<int:event_id>/cancel", methods=["POST"])
@role("organizer")
def organizer_cancel_event(event_id):
    if is_mine(event_id):
        cancel_event(event_id)
        flash("Event cancelled. Payments marked as refunded.", "success")
    return redirect(url_for("dashboard"))


# ---------- admin ----------
@app.route("/admin/events")
@role("admin")
def manage_events():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    sql = ("SELECT e.*, o.Organizer_Name, " + BOOKED + " AS Booked_Seats FROM `Event` e "
           "LEFT JOIN Organizer o ON o.Organizer_ID=e.Organizer_ID "
           "WHERE (e.Event_Name LIKE %s OR e.Location LIKE %s OR o.Organizer_Name LIKE %s)")
    args = ["%" + q + "%"] * 3
    if status:
        sql += " AND e.Status=%s"
        args.append(status)
    return render_template("manage_events.html", q=q, selected_status=status,
                           events=query(sql + " ORDER BY e.Actual_Event_Date DESC", args))


@app.route("/admin/event/<int:event_id>/cancel", methods=["POST"])
@role("admin")
def admin_cancel_event(event_id):
    cancel_event(event_id)
    flash("Event cancelled. Payments marked as refunded.", "success")
    return redirect(url_for("manage_events"))


@app.route("/admin/halls", methods=["GET", "POST"])
@role("admin")
def manage_halls():
    if request.method == "POST":
        query("""INSERT INTO Hall (Hall_Name, Location, Capacity, Hall_Charges, Available_From,
                 Available_To, Availability_Status) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
              form("hall_name", "location", "capacity", "charges",
                   "available_from", "available_to", "status"), commit=True)
        flash("Hall added.", "success")
        return redirect(url_for("manage_halls"))
    return render_template("manage_halls.html", halls=query("SELECT * FROM Hall"))


@app.route("/admin/services", methods=["GET", "POST"])
@role("admin")
def manage_services():
    if request.method == "POST":
        query("INSERT INTO Service (Service_Name, Service_Type, Service_Cost, Is_Free) "
              "VALUES (%s,%s,%s,%s)",
              form("service_name", "service_type", "service_cost", "is_free"), commit=True)
        flash("Service added.", "success")
        return redirect(url_for("manage_services"))
    return render_template("manage_services.html", services=query("SELECT * FROM Service"))


@app.route("/admin/bookings")
@role("admin")
def view_bookings():
    q = request.args.get("q", "").strip()
    rows = query("""SELECT b.*, u.User_Name, e.Event_Name, h.Hall_Name, p.Payment_Status
                    FROM Booking b JOIN `User` u ON u.User_ID=b.User_ID
                    JOIN `Event` e ON e.Event_ID=b.Event_ID
                    LEFT JOIN Hall h ON h.Hall_ID=b.Hall_ID
                    LEFT JOIN Payment p ON p.Booking_ID=b.Booking_ID
                    WHERE u.User_Name LIKE %s OR e.Event_Name LIKE %s
                    ORDER BY b.Booking_ID DESC""", ("%" + q + "%",) * 2)
    total = sum(r["Total_Amt"] for r in rows if r["Payment_Status"] != "Refunded")
    return render_template("view_bookings.html", bookings=rows, total_amount=total, q=q)


@app.route("/admin/payments")
@role("admin")
def view_payments():
    status = request.args.get("status", "")
    mode = request.args.get("mode", "")
    sql = """SELECT p.*, u.User_Name, e.Event_Name FROM Payment p
             JOIN Booking b ON b.Booking_ID=p.Booking_ID
             JOIN `User` u ON u.User_ID=b.User_ID
             JOIN `Event` e ON e.Event_ID=b.Event_ID WHERE 1=1"""
    args = []
    if status:
        sql += " AND p.Payment_Status=%s"
        args.append(status)
    if mode:
        sql += " AND p.Payment_Mode=%s"
        args.append(mode)
    rows = query(sql + " ORDER BY p.Payment_ID DESC", args)
    summary = {"paid": sum(r["Amount"] for r in rows if r["Payment_Status"] == "Paid"),
               "refunded": sum(r["Amount"] for r in rows if r["Payment_Status"] == "Refunded")}
    return render_template("view_payments.html", payments=rows, summary=summary,
                           selected_status=status, selected_mode=mode)


@app.route("/admin/feedback")
@role("admin")
def view_feedback():
    event_id = request.args.get("event_id", type=int)
    rating = request.args.get("rating", type=int)
    sql = """SELECT f.Feedback_ID, u.User_Name, e.Event_Name, f.Rating, f.Comments
             FROM Feedback f JOIN `User` u ON u.User_ID=f.User_ID
             JOIN `Event` e ON e.Event_ID=f.Event_ID WHERE 1=1"""
    args = []
    if event_id:
        sql += " AND f.Event_ID=%s"
        args.append(event_id)
    if rating:
        sql += " AND f.Rating=%s"
        args.append(rating)
    rows = query(sql + " ORDER BY f.Feedback_ID DESC", args)
    avg = round(sum(r["Rating"] for r in rows) / len(rows), 1) if rows else 0
    return render_template("view_feedback.html", feedbacks=rows, avg_rating=avg,
                           events=query("SELECT Event_ID, Event_Name FROM `Event`"),
                           selected_event=event_id, selected_rating=rating)


# ---------- small routes made by action_route(name, url variable, role, SQL, go back to) ----------
action_route("delete_schedule", "schedule_id", "organizer",
             "DELETE s FROM Schedule s JOIN `Event` e ON e.Event_ID=s.Event_ID "
             "WHERE s.Schedule_ID=%s AND e.Organizer_ID=%s", "add_schedule", owner=True)
action_route("delete_offer", "offer_id", "organizer",
             "DELETE o FROM Offer_Discount o JOIN `Event` e ON e.Event_ID=o.Event_ID "
             "WHERE o.Offer_ID=%s AND e.Organizer_ID=%s", "add_offer", owner=True)
action_route("delete_staff", "staff_id", "organizer",
             "DELETE FROM Staff WHERE Staff_ID=%s AND Organizer_ID=%s", "add_staff", owner=True)
action_route("delete_hall", "hall_id", "admin",
             "DELETE FROM Hall WHERE Hall_ID=%s", "manage_halls")
action_route("toggle_hall", "hall_id", "admin",
             "UPDATE Hall SET Availability_Status=IF(Availability_Status='Available','Booked','Available') "
             "WHERE Hall_ID=%s", "manage_halls")
action_route("delete_service", "service_id", "admin",
             "DELETE FROM Service WHERE Service_ID=%s", "manage_services")
action_route("admin_complete_event", "event_id", "admin",
             "UPDATE `Event` SET Status='Completed' WHERE Event_ID=%s AND Status='Upcoming'",
             "manage_events")

if __name__ == "__main__":
    # Run locally with: python app.py
    app.run(debug=True, use_reloader=False)