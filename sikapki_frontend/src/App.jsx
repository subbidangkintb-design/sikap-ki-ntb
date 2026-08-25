import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import HomePage from './pages/HomePage.jsx'
import CekMerekPage from './pages/CekMerekPage.jsx'
import ChatbotPage from './pages/ChatbotPage.jsx'
import FaqPage from './pages/FaqPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'
import InformationCenterPage from './pages/InformationCenterPage.jsx'
import UserTestingPage from './pages/UserTestingPage.jsx'
import ConsultationStatusPage from './pages/ConsultationStatusPage.jsx'
import ServiceStatusPage from './pages/ServiceStatusPage.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/cek-merek" element={<CekMerekPage />} />
        <Route path="/chatbot" element={<ChatbotPage />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="/statistik" element={<DashboardPage />} />
        <Route path="/checklist" element={<ChecklistPage />} />
        <Route path="/informasi" element={<InformationCenterPage />} />
        <Route path="/uji-coba" element={<UserTestingPage />} />
        <Route path="/status-konsultasi/:pelacakanId" element={<ConsultationStatusPage />} />
        <Route path="/status-layanan" element={<ServiceStatusPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
