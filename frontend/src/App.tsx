import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ScanView from './pages/ScanView';
import ImageDetail from './pages/ImageDetail';
import History from './pages/History';
import Settings from './pages/Settings';
import NavBar from './components/NavBar';

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan" element={<ScanView />} />
        <Route path="/scan/:scanId" element={<ScanView />} />
        <Route path="/assessment/:id" element={<ImageDetail />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}
