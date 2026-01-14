import './DocumentCard.css'

interface DocumentCardProps {
  document: any
  type: string
  formatDate: (date: number | string) => string
}

interface DocumentCardProps {
  document: any
  type: string
  formatDate: (date: number | string) => string
  onClick?: () => void
}

import { getPartnerDocumentTypeName } from '../utils/partnerTerminology'

function DocumentCard({ document, type, formatDate, onClick }: DocumentCardProps) {
  const getDocumentTypeLabel = () => {
    // Map system document types to partner perspective
    switch (type) {
      case 'purchase':
        return 'Отгрузка'  // System purchase -> Partner sees shipment
      case 'purchase-return':
        return 'Возврат отгрузки'  // System purchase return -> Partner sees shipment return
      case 'wholesale':
        return 'Закупка'  // System wholesale -> Partner sees purchase
      case 'wholesale-return':
        return 'Возврат закупки'  // System wholesale return -> Partner sees purchase return
      case 'payment':
        return 'Платеж'
      default:
        return 'Документ'
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
            Сумма: {getTotal().toLocaleString('ru-RU', { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: 2 
            })}
            {getCurrency() && <span className="currency"> {getCurrency()}</span>}
          </div>
          {getExchangeRate() && (
            <div className="exchange-rate">
              Курс: {typeof getExchangeRate() === 'number' 
                ? getExchangeRate().toLocaleString('ru-RU', { 
                    minimumFractionDigits: 4, 
                    maximumFractionDigits: 4 
                  })
                : getExchangeRate()}
            </div>
          )}
        </div>
      )}
      {type === 'payment' && document.category && (
        <div className="document-payment-direction">
          {document.category.positive ? '💸 Выплачено' : '💰 Получено'}
        </div>
      )}
    </div>
  )
}

export default DocumentCard
