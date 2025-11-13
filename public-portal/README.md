# NTC Public WiFi Portal

React-based captive portal for public WiFi access with OTP verification and advertisement display.

## Features

✅ Mobile-first responsive design
✅ OTP-based authentication
✅ CNIC/Passport verification
✅ Advertisement display (images/videos)
✅ Terms & Conditions acceptance
✅ Admin portal design integration
✅ Session management
✅ Analytics tracking

## Setup Instructions

### 1. Install Dependencies

```bash
cd "D:\Codes\NTC\NTC Public Wifi\public-portal"
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The portal will be available at: http://localhost:3001

### 3. Build for Production

```bash
npm run build
```

Build output will be in the `dist` folder.

## Configuration

### Backend API URL

Edit `src/services/api.js` to change the backend URL:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

For production, use your actual backend URL:

```javascript
const API_BASE_URL = 'https://your-domain.com/api';
```

## Integration with Captive Portal

### URL Parameters

The portal expects these parameters from the captive portal:

- `mac` or `client_mac` - Client MAC address
- `ap_mac` - Access Point MAC address
- `ssid` - WiFi network name
- `url` - Original URL user tried to access (for redirect)

Example URL:
```
http://portal.domain.com?mac=AA:BB:CC:DD:EE:FF&ap_mac=11:22:33:44:55:66&ssid=NTC_WiFi&url=http://google.com
```

### Omada Controller Integration

Configure your Omada controller to redirect users to:
```
http://your-portal-url
```

## Admin Portal Design

The public portal automatically fetches design settings from the admin portal:

- Logo
- Background image
- Colors (primary, secondary, background, text)
- Font family
- Welcome title & text
- Terms & conditions
- Footer text

Update these settings in the admin portal at:
```
Admin Portal → Portal Design
```

## File Structure

```
public-portal/
├── src/
│   ├── components/
│   │   ├── LoginForm.jsx      # OTP login & registration
│   │   ├── AdDisplay.jsx       # Advertisement display
│   │   ├── SuccessPage.jsx     # Success & redirect
│   │   └── TermsModal.jsx      # Terms popup
│   ├── services/
│   │   └── api.js              # API service
│   ├── App.jsx                 # Main app component
│   ├── index.css               # Styles
│   └── main.jsx                # Entry point
├── index.html
├── package.json
└── vite.config.js
```

## API Endpoints Used

### Public APIs (no authentication)
- `GET /api/portal/design` - Get portal design
- `GET /api/public/ads/active` - Get active ads
- `POST /api/public/ads/track` - Track ad events
- `POST /api/public/send-otp` - Send OTP
- `POST /api/public/verify-otp` - Verify OTP
- `POST /api/public/register` - Register user
- `POST /api/public/authorize` - Authorize WiFi access

## Testing

### Test Without Captive Portal

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd public-portal && npm run dev`
3. Open: http://localhost:3001

### Test With Mock Parameters

```
http://localhost:3001?mac=AA:BB:CC:DD:EE:FF&ssid=TestWiFi
```

## Production Deployment

### Option 1: Static Hosting (Nginx)

1. Build the app:
   ```bash
   npm run build
   ```

2. Copy `dist/` folder to your web server

3. Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name portal.yourdomain.com;
       
       root /path/to/dist;
       index index.html;
       
       location / {
           try_files $uri $uri/ /index.html;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Option 2: Docker

Create `Dockerfile`:
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build and run:
```bash
docker build -t ntc-public-portal .
docker run -p 80:80 ntc-public-portal
```

## Troubleshooting

### CORS Errors

Make sure backend CORS is configured to allow requests from your frontend URL:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### OTP Not Received

1. Check SMS service configuration in backend
2. Verify mobile number format (03XXXXXXXXX)
3. Check backend logs for errors

### Design Not Loading

1. Ensure admin portal has an active design configured
2. Check backend endpoint: http://localhost:8000/api/portal/design
3. Run initialization script:
   ```bash
   cd backend
   python initialize_defaults.py
   ```

## Support

For issues or questions, contact the development team.

## License

© 2024 NTC. All rights reserved.
