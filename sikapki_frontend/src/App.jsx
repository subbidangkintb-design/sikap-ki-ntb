import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import HomePage from './pages/HomePage.jsx'
import CekMerekPage from './pages/CekMerekPage.jsx'
import ChatbotPage from './pages/ChatbotPage.jsx'
import FaqPage from './pages/FaqPage.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/cek-merek" element={<CekMerekPage />} />
        <Route path="/chatbot" element={<ChatbotPage />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
