import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import './UserManagement.css'

interface User {
  user_id: number
  username: string | null
  email: string | null
  created_at: string
}

interface UserManagementProps {
  onUpdate?: () => void
}

function UserManagement({ onUpdate }: UserManagementProps) {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [formData, setFormData] = useState({ username: '', email: '', password: '' })
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const response = await api.get('/users')
      // Ensure response is an array
      setUsers(Array.isArray(response.data) ? response.data : [])
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch users')
      setUsers([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      const payload: any = {
        username: formData.username || null,
        email: formData.email || null,
      }
      if (formData.password) {
        payload.password = formData.password
      }
      await api.post('/users', payload)
      setShowModal(false)
      setEditingUser(null)
      setFormData({ username: '', email: '', password: '' })
      fetchUsers()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create user')
    }
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    setFormData({ username: user.username || '', email: user.email || '', password: '' })
    setShowModal(true)
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    
    try {
      setError('')
      const payload: any = {
        username: formData.username || null,
        email: formData.email || null,
      }
      // Only include password if provided
      if (formData.password) {
        payload.password = formData.password
      }
      await api.patch(`/users/${editingUser.user_id}`, payload)
      setShowModal(false)
      setEditingUser(null)
      setFormData({ username: '', email: '', password: '' })
      fetchUsers()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user')
    }
  }

  const handleDelete = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user? All associated tokens will also be deleted.')) {
      return
    }

    try {
      setDeletingId(userId)
      await api.delete(`/users/${userId}`)
      fetchUsers()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete user')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return <div className="loading">Loading users...</div>
  }

  return (
    <div className="user-management">
      <div className="section-header">
        <h2>User Management</h2>
        <button onClick={() => {
          setEditingUser(null)
          setFormData({ username: '', email: '', password: '' })
          setShowModal(true)
        }} className="add-button">
          + Add User
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {users.length === 0 ? (
        <div className="empty-state">No users found. Create your first user!</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Created At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.user_id}>
                <td data-label="ID">{user.user_id}</td>
                <td data-label="Username">{user.username || '-'}</td>
                <td data-label="Email">{user.email || '-'}</td>
                <td data-label="Created At">{new Date(user.created_at).toLocaleString()}</td>
                <td data-label="Actions">
                  <div className="action-buttons">
                    <button
                      onClick={() => handleEdit(user)}
                      className="edit-button"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(user.user_id)}
                      disabled={deletingId === user.user_id}
                      className="delete-button"
                    >
                      {deletingId === user.user_id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => {
          setShowModal(false)
          setEditingUser(null)
          setFormData({ username: '', email: '', password: '' })
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{editingUser ? 'Edit User' : 'Create New User'}</h3>
            <form onSubmit={editingUser ? handleUpdate : handleCreate}>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div className="form-group">
                <label>Password {!editingUser && '*'}</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder={editingUser ? "Leave empty to keep current password" : "Set initial password"}
                  required={!editingUser}
                />
                {editingUser && (
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    Enter new password to update, or leave empty to keep current password
                  </small>
                )}
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingUser(null)
                    setFormData({ username: '', email: '', password: '' })
                  }}
                  className="cancel-button"
                >
                  Cancel
                </button>
                <button type="submit" className="submit-button">
                  {editingUser ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserManagement

