import { useState, useEffect } from 'react'
import DocumentCard from './DocumentCard'
import DocumentDetail from './DocumentDetail'
import PartnerBalance from './PartnerBalance'
import { apiFetch } from '../utils/api'
import './DocumentList.css'

interface Document {
  id: number
  code: string
  date: number | string
  total?: number
  [key: string]: any
}

interface DocumentListProps {
  telegramUserId: number
  partnerId: number
  onBack?: () => void
}

type DocumentType = 'purchase' | 'purchase-return' | 'wholesale' | 'wholesale-return' | 'payment' | 'balance'

interface DocumentTotals {
  [documentType: string]: {
    [currency: string]: number
  }
}

function DocumentList({ telegramUserId, partnerId, onBack }: DocumentListProps) {
  const [activeTab, setActiveTab] = useState<DocumentType>('purchase')
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<{ id: number; type: 'purchase' | 'purchase-return' | 'wholesale' | 'wholesale-return' } | null>(null)
  const [showDatePicker, setShowDatePicker] = useState(false)
  const [documentTotals, setDocumentTotals] = useState<DocumentTotals>({})
  const [showTotalsSection, setShowTotalsSection] = useState(false)

  // Set default dates to current month
  const getCurrentMonthDates = () => {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)

    return {
      start: firstDay.toISOString().split('T')[0],
      end: lastDay.toISOString().split('T')[0]
    }
  }

  const [startDate, setStartDate] = useState(getCurrentMonthDates().start)
  const [endDate, setEndDate] = useState(getCurrentMonthDates().end)

  useEffect(() => {
    fetchDocuments()
    fetchAllDocumentTotals()
  }, [activeTab, telegramUserId, partnerId, startDate, endDate])

  // Helper function to get currency from a document
  const getCurrencyFromDocument = (doc: Document, docType: DocumentType): string => {
    if (docType === 'payment') {
      // For payment documents, currency is in type.account.currency
      if (doc.type?.account?.currency) {
        return typeof doc.type.account.currency === 'object'
          ? doc.type.account.currency.name || 'Unknown'
          : 'Unknown'
      }
    } else {
      // For other documents, currency is directly on the document
      if (doc.currency) {
        return typeof doc.currency === 'object'
          ? doc.currency.name || 'Unknown'
          : 'Unknown'
      }
    }
    return 'Unknown'
  }

  // Helper function to get amount from a document
  const getAmountFromDocument = (doc: Document, docType: DocumentType): number => {
    if (docType === 'payment') {
      return doc.amount || 0
    }
    return doc.total || doc.total_amount || doc.amount || 0
  }

  // Fetch totals for all document types
  const fetchAllDocumentTotals = async () => {
    const types: DocumentType[] = ['purchase', 'purchase-return', 'wholesale', 'wholesale-return', 'payment']
    const totals: DocumentTotals = {}

    try {
      await Promise.all(types.map(async (type) => {
        let endpoint = ''
        switch (type) {
          case 'purchase':
            endpoint = '/telegram-webapp/documents/purchase'
            break
          case 'purchase-return':
            endpoint = '/telegram-webapp/documents/purchase-return'
            break
          case 'wholesale':
            endpoint = '/telegram-webapp/documents/wholesale'
            break
          case 'wholesale-return':
            endpoint = '/telegram-webapp/documents/wholesale-return'
            break
          case 'payment':
            endpoint = '/telegram-webapp/documents/payment'
            break
        }

        const url = `${endpoint}?telegram_user_id=${telegramUserId}&partner_id=${partnerId}&start_date=${startDate}&end_date=${endDate}`
        const response = await apiFetch(url)
        const data = await response.json()

        if (data.ok) {
          let docs: Document[] = []
          if (type === 'payment') {
            docs = [
              ...(data.documents.income || []),
              ...(data.documents.outcome || [])
            ]
          } else {
            docs = data.documents || []
          }

          // Calculate totals by currency
          const typeTotals: { [currency: string]: number } = {}
          docs.forEach((doc: Document) => {
            const currency = getCurrencyFromDocument(doc, type)
            const amount = getAmountFromDocument(doc, type)
            typeTotals[currency] = (typeTotals[currency] || 0) + amount
          })

          totals[type] = typeTotals
        }
      }))

      setDocumentTotals(totals)
    } catch (err) {
      console.error('Error fetching document totals:', err)
    }
  }

  // Close date picker when clicking outside
  useEffect(() => {
    if (!showDatePicker) return

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('.date-filter-section')) {
        setShowDatePicker(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showDatePicker])

  const fetchDocuments = async () => {
    setIsLoading(true)
    setError(null)

    try {
      let endpoint = ''
      switch (activeTab) {
        case 'purchase':
          endpoint = '/telegram-webapp/documents/purchase'
          break
        case 'purchase-return':
          endpoint = '/telegram-webapp/documents/purchase-return'
          break
        case 'wholesale':
          endpoint = '/telegram-webapp/documents/wholesale'
          break
        case 'wholesale-return':
          endpoint = '/telegram-webapp/documents/wholesale-return'
          break
        case 'payment':
          endpoint = '/telegram-webapp/documents/payment'
          break
      }

      const url = `${endpoint}?telegram_user_id=${telegramUserId}&partner_id=${partnerId}&start_date=${startDate}&end_date=${endDate}`
      const response = await apiFetch(url)
      const data = await response.json()

      if (data.ok) {
        if (activeTab === 'payment') {
          // Payment documents have income and outcome arrays
          const allPayments = [
            ...(data.documents.income || []),
            ...(data.documents.outcome || [])
          ]
          setDocuments(allPayments)
        } else {
          setDocuments(data.documents || [])
        }
      } else {
        setError('Failed to fetch documents')
      }
    } catch (err) {
      setError('Error loading documents')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (date: number | string) => {
    if (typeof date === 'number') {
      return new Date(date * 1000).toLocaleDateString('ru-RU')
    }
    return new Date(date).toLocaleDateString('ru-RU')
  }

  // If a document is selected, show detail view
  if (selectedDocument) {
    return (
      <DocumentDetail
        documentId={selectedDocument.id}
        documentType={selectedDocument.type}
        telegramUserId={telegramUserId}
        partnerId={partnerId}
        onBack={() => setSelectedDocument(null)}
      />
    )
  }

  const handleDateChange = () => {
    if (startDate && endDate && startDate <= endDate) {
      setShowDatePicker(false)
      // fetchDocuments will be called automatically via useEffect
    }
  }

  const resetToCurrentMonth = () => {
    const dates = getCurrentMonthDates()
    setStartDate(dates.start)
    setEndDate(dates.end)
    setShowDatePicker(false)
  }

  return (
    <div className="document-list">
      {onBack && (
        <button className="back-button-icon" onClick={onBack} aria-label="Назад">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}
      <div className="header-section">
        <div className="tabs">
          <button
            className={activeTab === 'purchase' ? 'active' : ''}
            onClick={() => setActiveTab('purchase')}
          >
            Отгрузки
          </button>
          <button
            className={activeTab === 'purchase-return' ? 'active' : ''}
            onClick={() => setActiveTab('purchase-return')}
          >
            Возврат отгрузок
          </button>
          <button
            className={activeTab === 'wholesale' ? 'active' : ''}
            onClick={() => setActiveTab('wholesale')}
          >
            Закупки
          </button>
          <button
            className={activeTab === 'wholesale-return' ? 'active' : ''}
            onClick={() => setActiveTab('wholesale-return')}
          >
            Возврат закупок
          </button>
        <button
          className={activeTab === 'payment' ? 'active' : ''}
          onClick={() => setActiveTab('payment')}
        >
          Платежи
        </button>
        <button
          className={activeTab === 'balance' ? 'active' : ''}
          onClick={() => setActiveTab('balance')}
        >
          Баланс
        </button>
      </div>

        <div className="date-filter-section">
          <button
            className="calendar-button"
            onClick={() => setShowDatePicker(!showDatePicker)}
            title="Выбрать период"
          >
            📅
          </button>
          {showDatePicker && (
            <div className="date-picker-popup">
              <div className="date-picker-header">
                <span>Выберите период</span>
                <button className="close-button" onClick={() => setShowDatePicker(false)}>×</button>
              </div>
              <div className="date-inputs">
                <div className="date-input-group">
                  <label>С:</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    max={endDate}
                  />
                </div>
                <div className="date-input-group">
                  <label>По:</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={startDate}
                  />
                </div>
              </div>
              <div className="date-picker-actions">
                <button className="reset-button" onClick={resetToCurrentMonth}>
                  Текущий месяц
                </button>
                <button className="apply-button" onClick={handleDateChange}>
                  Применить
                </button>
              </div>
            </div>
          )}
          {!showDatePicker && (
            <div className="date-range-display">
              {new Date(startDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })} - {new Date(endDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })}
            </div>
          )}
          {Object.keys(documentTotals).length > 0 && (
            <button
              className={`totals-toggle-button-icon ${showTotalsSection ? 'active' : ''}`}
              onClick={() => setShowTotalsSection(!showTotalsSection)}
              title="Итого по типам документов"
            >
              📊
            </button>
          )}
        </div>
      </div>

      {/* Document Type Totals Section */}
      {showTotalsSection && Object.keys(documentTotals).length > 0 && (
        <div className="document-totals-section">
          <div className="totals-grid">
            {Object.entries(documentTotals).map(([type, currencyTotals]) => {
              const typeLabels: { [key: string]: string } = {
                'purchase': 'Отгрузки',  // System purchase -> Partner sees shipment
                'purchase-return': 'Возврат отгрузок',  // System purchase return -> Partner sees shipment return
                'wholesale': 'Закупки',  // System wholesale -> Partner sees purchase
                'wholesale-return': 'Возврат закупок',  // System wholesale return -> Partner sees purchase return
                'payment': 'Платежи'
              }

              const typeLabel = typeLabels[type] || type
              const hasTotals = Object.keys(currencyTotals).length > 0 &&
                Object.values(currencyTotals).some(v => v !== 0)

              if (!hasTotals) return null

              return (
                <div key={type} className="total-item">
                  <div className="total-item-label">{typeLabel}:</div>
                  <div className="total-item-amounts">
                    {Object.entries(currencyTotals)
                      .filter(([_, amount]) => amount !== 0)
                      .map(([currency, amount]) => (
                        <span key={currency} className="total-amount-item">
                          {amount.toLocaleString('ru-RU', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })} {currency}
                        </span>
                      ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {activeTab === 'balance' ? (
        <PartnerBalance
          telegramUserId={telegramUserId}
          partnerId={partnerId}
          startDate={startDate}
          endDate={endDate}
        />
      ) : isLoading ? (
        <div className="loading-state">Loading...</div>
      ) : error ? (
        <div className="error-state">{error}</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">No documents found</div>
      ) : (
        <div className="documents">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              type={activeTab}
              formatDate={formatDate}
              onClick={(() => {
                if (activeTab === 'purchase' || activeTab === 'purchase-return' || activeTab === 'wholesale' || activeTab === 'wholesale-return') {
                  return () => setSelectedDocument({ id: doc.id, type: activeTab })
                }
                return undefined
              })()}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default DocumentList
