# UHMS - Backend


## 🚀 Setup & Installation

Follow these steps to set up the backend environment locally.

### 1. Navigate to the backend directory
Open your terminal and ensure you are in the `uhms-backend-main` folder:
```bash
cd uhms-backend-main
```
### 2. Create and Activate Virtual environment
It is highly recommended to run this project inside a virtual environment to manage dependencies and avoid conflicts.

#### On Windows

``` bash
# Create the environment
python -m venv venv

# activate the environment
venv\Scripts\activate
```

#### On MacOS/Linux

``` bash
# Create the environment
python3 -m venv venv

# Activate the environment
source venv/bin/activate
```

#### Note: Once activated, your terminal prompt should show (venv).


### 3. Install dependencies
Install all required packages from the requirements file:
``` bash
pip install -r requirements.txt
```

### 4. Run Migrations
Initialize the SQLite database:
``` bash
python manage.py migrate
```

### 5. Run the Server
Start the development server:
``` bash
python manage.py runserver
```

