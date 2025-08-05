# Delivery Executive Chatbot

An AI-powered chatbot specifically designed for delivery executives (drivers, couriers, and field agents) to serve as their digital assistant for work-related queries, operational support, and real-time problem-solving during deliveries.

## 🚀 Features

### Core Functionalities
- **Route Optimization**: Fastest routes, traffic updates, alternative paths
- **Delivery Status Management**: Update statuses, handle exceptions, manage delays
- **Customer Communication**: Generate professional messages for customers
- **Policy & Procedure Queries**: Company policies, delivery protocols, SOPs
- **Emergency Support**: Immediate assistance for accidents, breakdowns, security
- **Earnings & Performance**: Track earnings, delivery metrics, performance goals
- **Technical Support**: Troubleshoot app issues, GPS problems, device queries

### Key Features
- Multi-language support
- Voice input/output capability (ready for integration)
- Real-time data processing
- Offline functionality for basic queries
- Mobile-first design
- Secure authentication with JWT

## 🛠️ Technology Stack

- **Backend**: Python FastAPI
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **AI/NLP**: Claude API integration
- **Authentication**: JWT tokens with bcrypt password hashing
- **API Documentation**: Automatic OpenAPI/Swagger documentation

## 📋 Prerequisites

- Python 3.8 or higher
- Claude API key (get from [Anthropic Console](https://console.anthropic.com/))
- pip (Python package installer)

## ⚡ Quick Start

### 1. Clone/Download Project Files

Ensure you have all the project files in your directory:
```
delivery_chatbot/
├── main.py                 # FastAPI app with all routes
├── models.py              # SQLAlchemy database models
├── database.py            # Database configuration
├── schemas.py             # Pydantic models for request/response
├── services/
│   ├── __init__.py        # Services package init
│   ├── claude_service.py  # Claude API integration
│   ├── auth_service.py    # Authentication logic
│   └── delivery_service.py # Delivery-specific business logic
├── create_database.py     # Database setup script
├── setup.py               # Automated setup script
├── test_api.py           # API testing script
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── README.md             # This file
```

### 2. Get Your Claude API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account or log in
3. Generate an API key
4. Keep it secure - you'll need it for the next step

### 3. Run Automated Setup

```bash
# Run the automated setup script
python setup.py
```

The setup script will:
- Check Python version compatibility
- Install all required dependencies
- Verify your Claude API key setup
- Create and populate the SQLite database
- Test all imports and configurations

### 4. Update Environment Variables

Edit the `.env` file and replace the placeholder with your actual Claude API key:

```env
CLAUDE_API_KEY=your_actual_claude_api_key_here
```

### 5. Start the Server

```bash
# Option 1: Direct Python
python main.py

# Option 2: Using uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test the API

```bash
# Run comprehensive API tests
python test_api.py
```

## 📖 API Documentation

Once the server is running, visit:

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔐 Demo Credentials

The database comes pre-populated with test users:

| Username | Password | Role |
|----------|----------|------|
| demo_user | demo123 | Main demo account |
| john_doe | password123 | Test user |
| jane_smith | password123 | Test user |
| mike_wilson | password123 | Test user |
| sarah_johnson | password123 | Test user |

## 🧪 Testing the Chatbot

### Sample Queries to Try

1. **Policy Questions**:
   - "What should I do if a package is damaged?"
   - "Customer is not home, what's the procedure?"
   - "How do I handle a COD delivery?"

2. **Route & Navigation**:
   - "Best route to avoid traffic?"
   - "My GPS is not working, help!"
   - "Alternative route avoiding highways"

3. **Customer Communication**:
   - "Generate message for delivery delay"
   - "Customer contact template"
   - "Professional response for complaint"

4. **Emergency & Technical**:
   - "Vehicle breakdown protocol"
   - "App is not working properly"
   - "Emergency contact information"

5. **Performance & Earnings**:
   - "How are my earnings calculated?"
   - "Check today's performance"
   - "View delivery statistics"

### Using the API

1. **Login** to get access token:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "demo_user",
       "password": "demo123"
     }'
   ```

2. **Chat** with the bot:
   ```bash
   curl -X POST "http://localhost:8000/api/chat" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What should I do if customer is not available?"
     }'
   ```

## 📁 Project Structure

```
├── Backend Services
│   ├── main.py              # FastAPI routes and middleware
│   └── services/
│       ├── claude_service.py    # AI chat processing
│       ├── auth_service.py      # JWT authentication
│       └── delivery_service.py  # Business logic
├── Database Layer
│   ├── database.py          # SQLAlchemy configuration
│   ├── models.py           # Database models
│   └── schemas.py          # API request/response models
├── Setup & Testing
│   ├── create_database.py   # Database initialization
│   ├── setup.py            # Automated project setup
│   └── test_api.py         # Comprehensive API tests
└── Configuration
    ├── requirements.txt     # Python dependencies
    ├── .env                # Environment variables
    └── README.md           # Project documentation
```

## 🗄️ Database Schema

The SQLite database includes these main tables:

- **users**: Delivery executive profiles
- **deliveries**: Active and completed deliveries
- **conversations**: Chat history and context
- **knowledge_base**: Company policies and procedures
- **user_preferences**: User settings and preferences
- **delivery_logs**: Status change tracking
- **user_metrics**: Performance analytics

## 🔧 Configuration

### Environment Variables (.env)

```env
# Claude API Configuration
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=1000

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_here

# Database Configuration
DATABASE_URL=sqlite:///./delivery_chatbot.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

## 🚀 Deployment Options

### Local Development
- SQLite database (included)
- Python virtual environment
- Local Claude API calls

### Production Ready
- PostgreSQL database
- Docker containerization
- Environment-based configuration
- Load balancing support
- Monitoring and logging

## 🔒 Security Features

- JWT token-based authentication
- Bcrypt password hashing
- SQL injection protection via SQLAlchemy
- CORS middleware configuration
- Request validation with Pydantic
- Secure API key management

## 🎯 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Chat & AI
- `POST /api/chat` - Main chatbot endpoint
- `POST /api/knowledge/search` - Search knowledge base

### Delivery Management
- `GET /api/deliveries` - Get user deliveries
- `POST /api/deliveries/update-status` - Update delivery status

### User Management
- `GET /api/user/profile` - Get user profile
- `GET /api/user/preferences` - Get user preferences
- `POST /api/user/preferences` - Update preferences
- `POST /api/user/location` - Update current location

### Dashboard & Analytics
- `GET /api/dashboard/summary` - Dashboard overview
- `GET /health` - Health check

## 📱 Frontend Integration

The API is designed for mobile-first integration. Example React Native integration:

```javascript
// Login and get token
const login = async (username, password) => {
  const response = await fetch('http://localhost:8000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await response.json();
  return data.access_token;
};

// Chat with bot
const sendMessage = async (message, token) => {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  return await response.json();
};
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Error**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Claude API Error**: Verify your API key in `.env` file

3. **Database Error**: Delete `delivery_chatbot.db` and run setup again
   ```bash
   python create_database.py
   ```

4. **Permission Error**: Ensure you have write permissions in the directory

5. **Port Already in Use**: Change the port in `.env` or kill the existing process

### Getting Help

1. Check the logs in the terminal where you started the server
2. Visit `/docs` endpoint for interactive API testing
3. Run `python test_api.py` to diagnose issues
4. Ensure all required files are present

## 🔄 Development Workflow

1. **Make Changes**: Edit Python files
2. **Test Locally**: Use `python test_api.py`
3. **Check API Docs**: Visit `/docs` endpoint
4. **Database Changes**: Update models and run migrations
5. **Deploy**: Follow your deployment process

## 📈 Performance Optimization

- **Caching**: Implement Redis for conversation context
- **Database**: Use PostgreSQL for production
- **API Limits**: Implement rate limiting
- **Monitoring**: Add logging and metrics
- **CDN**: Use for static assets

## 🤝 Contributing

This is a template project designed for customization. Key areas for enhancement:

1. **Frontend**: Build React Native or Flutter mobile app
2. **Features**: Add voice input/output, real-time notifications
3. **Integration**: Connect with mapping services, delivery platforms
4. **Analytics**: Enhanced performance tracking and reporting
5. **Localization**: Multi-language support expansion

## 📄 License

This project is provided as a development template. Customize according to your needs and requirements.

## 🎯 Next Steps

1. **Customize Knowledge Base**: Add your company's specific policies
2. **Integrate Maps**: Add Google Maps or similar service
3. **Build Mobile App**: Create React Native frontend
4. **Add Voice Support**: Integrate speech-to-text/text-to-speech  
5. **Deploy**: Set up production environment
6. **Monitor**: Add logging and analytics
7. **Scale**: Implement load balancing and caching

---



For questions or support, check the API documentation at `/docs` when your server is running.