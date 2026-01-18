import { useState, useEffect } from 'react'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import { getInvertedDebitCreditLabels, getPartnerDocumentTypeName } from '../utils/partnerTerminology'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './PartnerBalance.css'

interface PartnerBalanceProps {
  telegramUserId: number
  partnerId: number
  startDate: string
  endDate: string
}

interface Firm {
  id: number
  name: string
  [key: string]: any
}

interface Currency {
  id: number
  name: string
  code_chr: string
  [key: string]: any
}

interface BalanceEntry {
  id: number
  date: number
  document_code: string
  document_id: number
  start_amount: number
  debit: number
  credit: number
  currency_amount: number
  exchange_rate: number
  currency: Currency
  firm: Firm
  document_type: {
    id: number
    name: string
  }
}

function PartnerBalance({ telegramUserId, partnerId, startDate, endDate }: PartnerBalanceProps) {
  const [firms, setFirms] = useState<Firm[]>([])
  const [currencies, setCurrencies] = useState<Currency[]>([])
  const [selectedFirms, setSelectedFirms] = useState<number[]>([])
  const [selectedCurrencies, setSelectedCurrencies] = useState<number[]>([])
  const [balance, setBalance] = useState<BalanceEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  
  // Get inverted labels for partner view
  const { debitLabel, creditLabel } = getInvertedDebitCreditLabels("ru")
  const [isLoadingBalance, setIsLoadingBalance] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFirmsAndCurrencies()
  }, [telegramUserId])

  useEffect(() => {
    if (selectedFirms.length > 0 && selectedCurrencies.length > 0) {
      fetchBalance()
    } else {
      setBalance([])
    }
  }, [selectedFirms, selectedCurrencies, startDate, endDate, telegramUserId, partnerId])

  const fetchFirmsAndCurrencies = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const [firmsResponse, currenciesResponse] = await Promise.all([
        apiFetch(`/telegram-webapp/firms?telegram_user_id=${telegramUserId}`),
        apiFetch(`/telegram-webapp/currencies?telegram_user_id=${telegramUserId}`)
      ])

      const firmsData = await firmsResponse.json()
      const currenciesData = await currenciesResponse.json()

      if (firmsData.ok) {
        setFirms(firmsData.firms || [])
      }
      if (currenciesData.ok) {
        setCurrencies(currenciesData.currencies || [])
      }
    } catch (err) {
      setError('Error loading firms and currencies')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchBalance = async () => {
    setIsLoadingBalance(true)
    setError(null)

    try {
      const firmIds = selectedFirms.join(',')
      const currencyIds = selectedCurrencies.join(',')

      const url = `/telegram-webapp/partner-balance?telegram_user_id=${telegramUserId}&partner_id=${partnerId}&start_date=${startDate}&end_date=${endDate}&firm_ids=${firmIds}&currency_ids=${currencyIds}`
      const response = await apiFetch(url)
      const data = await response.json()

      if (data.ok) {
        setBalance(data.balance || [])
      } else {
        setError('Failed to fetch balance')
      }
    } catch (err) {
      setError('Error loading balance')
    } finally {
      setIsLoadingBalance(false)
    }
  }

  const toggleFirm = (firmId: number) => {
    setSelectedFirms(prev =>
      prev.includes(firmId)
        ? prev.filter(id => id !== firmId)
        : [...prev, firmId]
    )
  }

  const toggleCurrency = (currencyId: number) => {
    setSelectedCurrencies(prev =>
      prev.includes(currencyId)
        ? prev.filter(id => id !== currencyId)
        : [...prev, currencyId]
    )
  }

  const formatDate = (date: number) => {
    return new Date(date * 1000).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const calculateRemainder = (entry: BalanceEntry) => {
    return entry.start_amount + entry.debit - entry.credit
  }

  const handleExport = async () => {
    if (selectedFirms.length === 0 || selectedCurrencies.length === 0) {
      setExportError('Выберите хотя бы одно предприятие и одну валюту')
      return
    }

    setIsExporting(true)
    setExportError(null)

    try {
      const firmIds = selectedFirms.join(',')
      const currencyIds = selectedCurrencies.join(',')

      const url = `/telegram-webapp/partner-balance/export?telegram_user_id=${telegramUserId}&partner_id=${partnerId}&start_date=${startDate}&end_date=${endDate}&firm_ids=${firmIds}&currency_ids=${currencyIds}`
      const response = await apiFetch(url, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.ok) {
        // Show success message
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.showAlert('Excel файл отправлен в ваш Telegram чат!')
        } else {
          alert('Excel файл отправлен в ваш Telegram чат!')
        }
      } else {
        setExportError(data.message || 'Ошибка при экспорте')
      }
    } catch (err) {
      setExportError('Ошибка при отправке файла')
    } finally {
      setIsExporting(false)
    }
  }

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  return (
    <div className="partner-balance">
      <div className="balance-header">
        <h2 className="balance-title">Баланс партнера</h2>
        {selectedFirms.length > 0 && selectedCurrencies.length > 0 && (
          <button
            className="export-balance-button"
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? '⏳ Отправка...' : '📥 Скачать Excel'}
          </button>
        )}
      </div>

      {exportError && (
        <div className="export-error">{exportError}</div>
      )}

      <div className="balance-filters">
        <div className="filter-section">
          <h3 className="filter-title">Предприятия</h3>
          <div className="checkbox-group">
            {firms.map(firm => (
              <label key={firm.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedFirms.includes(firm.id)}
                  onChange={() => toggleFirm(firm.id)}
                />
                <span>{firm.name}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="filter-section">
          <h3 className="filter-title">Валюты</h3>
          <div className="checkbox-group">
            {currencies.map(currency => (
              <label key={currency.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedCurrencies.includes(currency.id)}
                  onChange={() => toggleCurrency(currency.id)}
                />
                <span>{currency.name} ({currency.code_chr})</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {selectedFirms.length === 0 || selectedCurrencies.length === 0 ? (
        <div className="balance-placeholder">
          Выберите хотя бы одно предприятие и одну валюту для отображения баланса
        </div>
      ) : isLoadingBalance ? (
        <Loading />
      ) : balance.length === 0 ? (
        <div className="balance-empty">Нет данных о балансе за выбранный период</div>
      ) : (
        <div className="balance-list">
          {balance.map(entry => {
            const remainder = calculateRemainder(entry)
            return (
              <div key={entry.id} className="balance-entry">
                <div className="balance-entry-header">
                  <span className="balance-document-code">{entry.document_code}</span>
                  <span className="balance-date">{formatDate(entry.date)}</span>
                </div>
                <div className="balance-entry-details">
                  <div className="balance-detail-row">
                    <span className="balance-label">Тип документа:</span>
                    <span className="balance-value">{getPartnerDocumentTypeName(entry.document_type.name, "ru")}</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">Предприятие:</span>
                    <span className="balance-value">{entry.firm.name}</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">Валюта:</span>
                    <span className="balance-value">{entry.currency.name} ({entry.currency.code_chr})</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">Начальный остаток:</span>
                    <span className="balance-value">
                      {formatNumber(entry.start_amount)}
                    </span>
                  </div>
                  {/* Inverted for partner view: system credit -> partner debit */}
                  {entry.credit !== 0 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">{debitLabel}:</span>
                      <span className="balance-value debit">
                        +{formatNumber(entry.credit)}
                      </span>
                    </div>
                  )}
                  {/* Inverted for partner view: system debit -> partner credit */}
                  {entry.debit !== 0 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">{creditLabel}:</span>
                      <span className="balance-value credit">
                        -{formatNumber(entry.debit)}
                      </span>
                    </div>
                  )}
                  <div className="balance-detail-row total">
                    <span className="balance-label">Остаток:</span>
                    <span className={`balance-value ${remainder >= 0 ? 'positive' : 'negative'}`}>
                      {formatNumber(remainder)}
                    </span>
                  </div>
                  {entry.exchange_rate !== 1 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">Курс обмена:</span>
                      <span className="balance-value">
                        {formatNumber(entry.exchange_rate, 4)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default PartnerBalance
