import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './PakAppUsers.css';

const PakAppUsers = () => {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Pagination & Filters
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(50);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState('all');
  
  // Selected user for details
  const [selectedUser, setSelectedUser] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await api.get('/pakapp/stats');
      setStats(response.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Fetch users
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        page,
        per_page: perPage,
      };
      
      if (search) params.search = search;
      if (filterActive !== 'all') params.is_active = filterActive === 'active';
      
      const response = await api.get('/pakapp/users', { params });
      
      setUsers(response.data.users);
      setTotal(response.data.total);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch users');
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  // Toggle user active status
  const toggleUserStatus = async (userId, currentStatus) => {
    try {
      await api.patch(
        `/pakapp/users/${userId}`,
        { is_active: !currentStatus }
      );
      
      // Refresh users list
      fetchUsers();
      fetchStats();
    } catch (err) {
      alert('Failed to update user status');
      console.error('Error updating user:', err);
    }
  };

  // View user details
  const viewUserDetails = (user) => {
    setSelectedUser(user);
    setShowDetails(true);
  };

  // Export to CSV
  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'CNIC', 'Phone', 'Email', 'Active', 'Created At'];
    const csvData = users.map(user => [
      user.id,
      user.name,
      user.cnic,
      user.phone,
      user.email || '',
      user.is_active ? 'Yes' : 'No',
      new Date(user.created_at).toLocaleString()
    ]);
    
    const csv = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pakapp_users_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  useEffect(() => {
    fetchStats();
    fetchUsers();
  }, [page, perPage, search, filterActive]);

  // Calculate pagination
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="pakapp-users-container">
      <div className="page-header">
        <h1>📱 PakApp User Registrations</h1>
        <button onClick={exportToCSV} className="btn-export">
          📥 Export to CSV
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card stat-primary">
            <div className="stat-icon">👥</div>
            <div className="stat-content">
              <div className="stat-label">Total Users</div>
              <div className="stat-value">{stats.total_users.toLocaleString()}</div>
            </div>
          </div>
          
          <div className="stat-card stat-success">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <div className="stat-label">Active Users</div>
              <div className="stat-value">{stats.active_users.toLocaleString()}</div>
            </div>
          </div>
          
          <div className="stat-card stat-warning">
            <div className="stat-icon">⏸️</div>
            <div className="stat-content">
              <div className="stat-label">Inactive Users</div>
              <div className="stat-value">{stats.inactive_users.toLocaleString()}</div>
            </div>
          </div>
          
          <div className="stat-card stat-info">
            <div className="stat-icon">📅</div>
            <div className="stat-content">
              <div className="stat-label">Last 7 Days</div>
              <div className="stat-value">{stats.recent_registrations_7days.toLocaleString()}</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search by name, CNIC, phone, or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="search-input"
          />
        </div>
        
        <div className="filter-buttons">
          <button
            className={`filter-btn ${filterActive === 'all' ? 'active' : ''}`}
            onClick={() => {
              setFilterActive('all');
              setPage(1);
            }}
          >
            All Users
          </button>
          <button
            className={`filter-btn ${filterActive === 'active' ? 'active' : ''}`}
            onClick={() => {
              setFilterActive('active');
              setPage(1);
            }}
          >
            ✅ Active
          </button>
          <button
            className={`filter-btn ${filterActive === 'inactive' ? 'active' : ''}`}
            onClick={() => {
              setFilterActive('inactive');
              setPage(1);
            }}
          >
            ⏸️ Inactive
          </button>
        </div>
        
        <div className="per-page-selector">
          <label>Show:</label>
          <select
            value={perPage}
            onChange={(e) => {
              setPerPage(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
          <span>per page</span>
        </div>
      </div>

      {/* Users Table */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading users...</p>
        </div>
      ) : error ? (
        <div className="error-state">
          <p>❌ {error}</p>
          <button onClick={fetchUsers} className="btn-retry">Retry</button>
        </div>
      ) : users.length === 0 ? (
        <div className="empty-state">
          <p>📭 No users found</p>
          {search && <p className="hint">Try adjusting your search criteria</p>}
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>CNIC</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Registered</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td className="user-name">{user.name}</td>
                    <td className="cnic">{user.cnic}</td>
                    <td className="phone">{user.phone}</td>
                    <td className="email">{user.email || '-'}</td>
                    <td>
                      <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                        {user.is_active ? '✅ Active' : '⏸️ Inactive'}
                      </span>
                    </td>
                    <td className="date">
                      {new Date(user.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </td>
                    <td className="actions">
                      <button
                        onClick={() => viewUserDetails(user)}
                        className="btn-icon btn-view"
                        title="View Details"
                      >
                        👁️
                      </button>
                      <button
                        onClick={() => toggleUserStatus(user.id, user.is_active)}
                        className={`btn-icon ${user.is_active ? 'btn-deactivate' : 'btn-activate'}`}
                        title={user.is_active ? 'Deactivate' : 'Activate'}
                      >
                        {user.is_active ? '⏸️' : '▶️'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <div className="pagination-info">
              Showing {((page - 1) * perPage) + 1} to {Math.min(page * perPage, total)} of {total} users
            </div>
            
            <div className="pagination-controls">
              <button
                onClick={() => setPage(1)}
                disabled={page === 1}
                className="btn-page"
              >
                ⏮️ First
              </button>
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="btn-page"
              >
                ◀️ Previous
              </button>
              
              <span className="page-numbers">
                Page {page} of {totalPages}
              </span>
              
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className="btn-page"
              >
                Next ▶️
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page === totalPages}
                className="btn-page"
              >
                Last ⏭️
              </button>
            </div>
          </div>
        </>
      )}

      {/* User Details Modal */}
      {showDetails && selectedUser && (
        <div className="modal-overlay" onClick={() => setShowDetails(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>👤 User Details</h2>
              <button onClick={() => setShowDetails(false)} className="btn-close">✕</button>
            </div>
            
            <div className="modal-body">
              <div className="detail-row">
                <span className="detail-label">ID:</span>
                <span className="detail-value">{selectedUser.id}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Name:</span>
                <span className="detail-value">{selectedUser.name}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">CNIC:</span>
                <span className="detail-value">{selectedUser.cnic}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Phone:</span>
                <span className="detail-value">{selectedUser.phone}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Email:</span>
                <span className="detail-value">{selectedUser.email || 'Not provided'}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Status:</span>
                <span className="detail-value">
                  <span className={`status-badge ${selectedUser.is_active ? 'active' : 'inactive'}`}>
                    {selectedUser.is_active ? '✅ Active' : '⏸️ Inactive'}
                  </span>
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Source:</span>
                <span className="detail-value">{selectedUser.source}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">IP Address:</span>
                <span className="detail-value">{selectedUser.ip_address || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Created:</span>
                <span className="detail-value">
                  {new Date(selectedUser.created_at).toLocaleString()}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Last Updated:</span>
                <span className="detail-value">
                  {new Date(selectedUser.updated_at).toLocaleString()}
                </span>
              </div>
            </div>
            
            <div className="modal-footer">
              <button
                onClick={() => {
                  toggleUserStatus(selectedUser.id, selectedUser.is_active);
                  setShowDetails(false);
                }}
                className={`btn ${selectedUser.is_active ? 'btn-warning' : 'btn-success'}`}
              >
                {selectedUser.is_active ? '⏸️ Deactivate User' : '▶️ Activate User'}
              </button>
              <button onClick={() => setShowDetails(false)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PakAppUsers;
