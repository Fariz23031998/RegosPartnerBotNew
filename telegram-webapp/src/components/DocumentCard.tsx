import { formatNumber } from '../utils/formatNumber'
import './DocumentCard.css'
import { useLanguage } from '../contexts/LanguageContext'

interface DocumentCardProps {
  document: any
  type: string
  formatDate: (date: number | string) => string
  onClick?: () => void
}

function DocumentCard({ document, type, formatDate, onClick }: DocumentCardProps) {
  const { t } = useLanguage()
  
  const getDocumentTypeLabel = () => {
    // Map system document types to partner perspective
    switch (type) {
      case 'purchase':
        return t('document-card.type.shipment', 'Отгрузка')  // System purchase -> Partner sees shipment
      case 'purchase-return':
        return t('document-card.type.shipment-return', 'Возврат отгрузки')  // System purchase return -> Partner sees shipment return
      case 'wholesale':
        return t('document-card.type.purchase', 'Закупка')  // System wholesale -> Partner sees purchase
      case 'wholesale-return':
        return t('document-card.type.purchase-return', 'Возврат закупки')  // System wholesale return -> Partner sees purchase return
      case 'payment':
        return t('document-card.type.payment', 'Платеж')
      default:
        return t('document-card.type.document', 'Документ')
    }
  }

  const getTotal = () => {
    if (type === 'payment') {
      return document.amount || 0
    }
    return document.total || document.total_amount || document.amount || 0
  }

  const getCurrency = () => {
    // For payment documents, currency is nested in type.account.currency
    if (type === 'payment') {
      const account = document.type?.account
      if (account?.currency) {
        return typeof account.currency === 'object' 
          ? account.currency.name || '' 
          : ''
      }
      return ''
    }
    
    // For other document types, currency is directly on the document
    if (document.currency) {
      return typeof document.currency === 'object' 
        ? document.currency.name || '' 
        : ''
    }
    return ''
  }

  const getExchangeRate = () => {
    // For payment documents, exchange_rate is at root level
    // For other documents, it might be in currency.exchange_rate or at root
    let rate = document.exchange_rate
    
    // If not at root, try currency.exchange_rate
    if (!rate && document.currency && typeof document.currency === 'object') {
      rate = document.currency.exchange_rate
    }
    
    // For payment documents, also check type.account.currency.exchange_rate
    if (!rate && type === 'payment' && document.type?.account?.currency) {
      rate = document.type.account.currency.exchange_rate
    }
    
    // Convert to number if string
    if (typeof rate === 'string') {
      rate = parseFloat(rate)
    }
    
    // Return rate if it exists and is not 1
    if (rate != null && rate !== 1 && rate !== 1.0 && !isNaN(rate)) {
      return rate
    }
    return null
  }

  const isClickable = type !== 'payment' && onClick

  return (
    <div 
      className={`document-card ${isClickable ? 'clickable' : ''}`}
      onClick={isClickable ? onClick : undefined}
    >
      <div className="document-header">
        <span className="document-type">{getDocumentTypeLabel()}</span>
        <span className="document-code">№{document.code || document.id}</span>
      </div>
      <div className="document-date">
        {formatDate(document.date)}
      </div>
      {getTotal() > 0 && (
        <div className="document-total">
          <div className="total-amount">
            {t('document-card.total', 'Сумма:')} {formatNumber(getTotal())}
            {getCurrency() && <span className="currency"> {getCurrency()}</span>}
          </div>
          {getExchangeRate() && (
            <div className="exchange-rate">
              {t('document-card.exchange-rate', 'Курс:')} {typeof getExchangeRate() === 'number' 
                ? formatNumber(getExchangeRate(), 4)
                : getExchangeRate()}
            </div>
          )}
        </div>
      )}
      {type === 'payment' && document.category && (
        <div className="document-payment-direction">
          {document.category.positive ? t('document-card.payment-direction.paid', '💸 Выплачено') : t('document-card.payment-direction.received', '💰 Получено')}
        </div>
      )}
    </div>
  )
}

export default DocumentCard
