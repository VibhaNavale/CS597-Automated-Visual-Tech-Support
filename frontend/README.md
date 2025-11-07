# Video Analysis Frontend

A React + Redux frontend for the Video Analysis API that provides an intuitive interface for analyzing video tutorials and extracting step-by-step UI interactions using OS-Atlas.

## Features

- **Query Input**: Clean interface for entering video analysis queries
- **Processing Pipeline**: Real-time visualization of the analysis steps
- **Results Display**: Step-by-step breakdown with bounding boxes and actions
- **Error Handling**: User-friendly error messages and retry functionality
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **React 18** with TypeScript
- **Redux Toolkit** for state management
- **Tailwind CSS** for styling
- **Vite** for build tooling
- **Axios** for API communication

## Getting Started

### Prerequisites

- Node.js 16+ 
- npm or yarn

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:3000`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## API Integration

The frontend is configured to connect to the remote API at:
```
https://compaasgold06.evl.uic.edu/api-vnava22
```

### API Endpoints

- **POST /process-query**: Processes video analysis queries
- **GET /health**: Health check endpoint

## Project Structure

```
src/
├── components/          # React components
│   ├── Header.tsx      # Application header
│   ├── QueryInput.tsx  # Query input form
│   ├── ProcessingPipeline.tsx  # Processing steps visualization
│   ├── ResultsDisplay.tsx      # Results display
│   └── ErrorDisplay.tsx        # Error handling
├── store/              # Redux store
│   ├── store.ts        # Store configuration
│   └── slices/         # Redux slices
│       └── videoAnalysisSlice.ts
├── services/           # API services
│   └── api.ts         # API client configuration
├── App.tsx            # Main application component
├── main.tsx           # Application entry point
└── index.css          # Global styles
```

## Usage

1. **Enter Query**: Type your video analysis question in the input field
2. **Start Analysis**: Click "Analyze" to begin processing
3. **Monitor Progress**: Watch the processing pipeline for real-time updates
4. **View Results**: See step-by-step breakdown with visualizations and actions

## Customization

### Styling
The application uses Tailwind CSS with a custom color scheme. You can modify colors in `tailwind.config.js`.

### API Configuration
Update the API base URL in `src/services/api.ts` if needed.

### Processing Steps
Modify the processing steps in `src/store/slices/videoAnalysisSlice.ts`.

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

### State Management

The application uses Redux Toolkit for state management with the following main state:

- `query`: Current analysis query
- `isProcessing`: Whether analysis is in progress
- `steps`: Processing pipeline steps
- `results`: Analysis results from OS-Atlas
- `error`: Error messages
- `progress`: Overall progress percentage

## Troubleshooting

### Common Issues

1. **API Connection Errors**: Check if the remote API is accessible
2. **CORS Issues**: Ensure the API has proper CORS configuration
3. **Timeout Errors**: The API has a 5-minute timeout for long processing

### Debug Mode

Enable debug logging by opening browser developer tools and checking the console for API request/response logs.
