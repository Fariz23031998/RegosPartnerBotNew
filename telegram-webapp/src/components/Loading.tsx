import './Loading.css'
import { useLanguage } from '../contexts/LanguageContext'
function Loading() {
  const { t } = useLanguage()
  return (
    <div className="loading">
      <div className="spinner"></div>
      <p>{t("loading.loading", "Loading...")}</p>
    </div>
  )
}

export default Loading
