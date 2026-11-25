import { useEffect, useState } from "react";

export default function App() {
  const [groups, setGroups] = useState([]);
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [members, setMembers] = useState([]);
  const [debts, setDebts] = useState([]);
  const [summary, setSummary] = useState([]);
  const [error, setError] = useState("");

  // Formularz dodawania uczestnika
  const [newMemberName, setNewMemberName] = useState("");

  // Formularz dodawania długu
  const [debtFrom, setDebtFrom] = useState("");
  const [debtTo, setDebtTo] = useState("");
  const [debtAmount, setDebtAmount] = useState("");
  const [debtTitle, setDebtTitle] = useState("");

  // Modal nowej grupy
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");

  // Modal edycji długu
  const [editingDebt, setEditingDebt] = useState(null);

  // Pomocnicza funkcja zapytań do API
  async function apiRequest(url, options = {}) {
    setError("");
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Wystąpił błąd komunikacji z serwerem.");
    }
    return data;
  }

  // Pobranie listy grup
  async function loadGroups(preferredId = null) {
    try {
      const data = await apiRequest("/api/groups");
      setGroups(data);
      if (data.length === 0) {
        setActiveGroupId(null);
      } else if (preferredId && data.some((g) => g.id === preferredId)) {
        setActiveGroupId(preferredId);
      } else if (!data.some((g) => g.id === activeGroupId)) {
        setActiveGroupId(data[0].id);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  // Pobranie uczestników, długów i bilansu dla wybranej grupy
  async function loadGroupDetails(groupId) {
    if (!groupId) {
      setMembers([]);
      setDebts([]);
      setSummary([]);
      return;
    }
    try {
      const [membersData, debtsData, summaryData] = await Promise.all([
        apiRequest(`/api/groups/${groupId}/members`),
        apiRequest(`/api/groups/${groupId}/debts`),
        apiRequest(`/api/groups/${groupId}/summary`),
      ]);
      setMembers(membersData);
      setDebts(debtsData);
      setSummary(summaryData);

      // Ustawienie domyślnych osób w selectach formularza
      if (membersData.length >= 2) {
        setDebtFrom((prev) =>
          membersData.some((m) => m.name === prev) ? prev : membersData[0].name
        );
        setDebtTo((prev) =>
          membersData.some((m) => m.name === prev) ? prev : membersData[1].name
        );
      } else if (membersData.length === 1) {
        setDebtFrom(membersData[0].name);
        setDebtTo(membersData[0].name);
      } else {
        setDebtFrom("");
        setDebtTo("");
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadGroups();
  }, []);

  useEffect(() => {
    loadGroupDetails(activeGroupId);
  }, [activeGroupId]);

  const activeGroup = groups.find((g) => g.id === activeGroupId) || null;

  // --- Akcje grup ---
  async function handleCreateGroup(e) {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    try {
      const created = await apiRequest("/api/groups", {
        method: "POST",
        body: JSON.stringify({ name: newGroupName }),
      });
      setNewGroupName("");
      setShowGroupModal(false);
      await loadGroups(created.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteGroup() {
    if (!activeGroup) return;
    if (!window.confirm(`Czy na pewno usunąć grupę "${activeGroup.name}"?`)) {
      return;
    }
    try {
      await apiRequest(`/api/groups/${activeGroup.id}`, { method: "DELETE" });
      await loadGroups();
    } catch (err) {
      setError(err.message);
    }
  }

  // --- Akcje uczestników ---
  async function handleAddMember(e) {
    e.preventDefault();
    if (!newMemberName.trim() || !activeGroupId) return;
    try {
      await apiRequest(`/api/groups/${activeGroupId}/members`, {
        method: "POST",
        body: JSON.stringify({ name: newMemberName }),
      });
      setNewMemberName("");
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRemoveMember(memberId) {
    try {
      await apiRequest(`/api/members/${memberId}`, { method: "DELETE" });
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  // --- Akcje rozliczeń ---
  async function handleAddDebt(e) {
    e.preventDefault();
    if (!activeGroupId) return;
    try {
      await apiRequest(`/api/groups/${activeGroupId}/debts`, {
        method: "POST",
        body: JSON.stringify({
          debt_from: debtFrom,
          debt_to: debtTo,
          amount: parseFloat(debtAmount),
          title: debtTitle,
        }),
      });
      setDebtAmount("");
      setDebtTitle("");
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSaveEditDebt(e) {
    e.preventDefault();
    if (!editingDebt) return;
    try {
      await apiRequest(`/api/debts/${editingDebt.id}`, {
        method: "PUT",
        body: JSON.stringify({
          debt_from: editingDebt.debt_from,
          debt_to: editingDebt.debt_to,
          amount: parseFloat(editingDebt.amount),
          title: editingDebt.title || "",
        }),
      });
      setEditingDebt(null);
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleSettle(debtId) {
    try {
      await apiRequest(`/api/debts/${debtId}/settle`, { method: "PATCH" });
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteDebt(debtId) {
    try {
      await apiRequest(`/api/debts/${debtId}`, { method: "DELETE" });
      await loadGroupDetails(activeGroupId);
    } catch (err) {
      setError(err.message);
    }
  }

  // Lista opcji osób przy edycji (uwzględnia także dawnych członków)
  const memberNames = members.map((m) => m.name);
  const editPeopleOptions = editingDebt
    ? Array.from(
        new Set([...memberNames, editingDebt.debt_from, editingDebt.debt_to])
      )
    : memberNames;

  return (
    <>
      <nav className="navbar">
        <div className="nav-brand">
          <span className="logo-icon">💸</span>
          <strong>MoneyApp</strong>
        </div>

        <div className="nav-actions">
          {groups.length > 0 && (
            <div className="group-select-wrapper">
              <label htmlFor="group-select">Aktywna grupa:</label>
              <select
                id="group-select"
                value={activeGroupId || ""}
                onChange={(e) => setActiveGroupId(Number(e.target.value))}
              >
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            id="btn-modal-new-group"
            className="btn btn-sm btn-outline"
            onClick={() => setShowGroupModal(true)}
          >
            + Nowa grupa
          </button>
        </div>
      </nav>

      <main className="container">
        {error && (
          <div className="error-alert">
            <span>{error}</span>
            <button
              type="button"
              className="btn-danger-text"
              onClick={() => setError("")}
            >
              ✕
            </button>
          </div>
        )}

        {!activeGroup ? (
          <section className="box">
            <h2>Brak aktywnych grup</h2>
            <p className="empty-text">
              Utwórz pierwszą grupę klikając przycisk{" "}
              <strong>+ Nowa grupa</strong> w prawym górnym rogu.
            </p>
          </section>
        ) : (
          <>
            <header className="group-header">
              <div>
                <h1 id="current-group-title">{activeGroup.name}</h1>
                <p className="subtitle">
                  Zarządzaj uczestnikami i wpisuj rozliczenia
                </p>
              </div>
              <button
                id="btn-delete-group"
                className="btn btn-danger-text"
                onClick={handleDeleteGroup}
              >
                Usuń tę grupę
              </button>
            </header>

            <div className="grid-layout">
              {/* Uczestnicy grupy */}
              <section className="box">
                <h2>Uczestnicy grupy</h2>

                <form
                  id="add-member-form"
                  className="inline-form"
                  onSubmit={handleAddMember}
                >
                  <input
                    type="text"
                    id="new-member-name"
                    placeholder="Imię nowego członka..."
                    value={newMemberName}
                    onChange={(e) => setNewMemberName(e.target.value)}
                    required
                  />
                  <button type="submit" className="btn btn-primary">
                    Dodaj
                  </button>
                </form>

                {members.length === 0 ? (
                  <p className="empty-text">
                    Dodaj uczestników, aby móc dzielić wydatki.
                  </p>
                ) : (
                  <ul id="members-list" className="badge-list">
                    {members.map((m) => (
                      <li key={m.id} className="badge">
                        <span>{m.name}</span>
                        <button
                          type="button"
                          className="remove-btn"
                          title="Usuń uczestnika"
                          onClick={() => handleRemoveMember(m.id)}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* Dodaj rozliczenie */}
              <section className="box">
                <h2>Dodaj rozliczenie</h2>

                {members.length < 2 ? (
                  <p className="empty-text">
                    Potrzeba co najmniej 2 uczestników w grupie, aby dodać
                    rozliczenie.
                  </p>
                ) : (
                  <form id="debt-form" onSubmit={handleAddDebt}>
                    <div className="form-row">
                      <div className="form-group">
                        <label htmlFor="debt-from">Kto oddaje:</label>
                        <select
                          id="debt-from"
                          value={debtFrom}
                          onChange={(e) => setDebtFrom(e.target.value)}
                          required
                        >
                          {members.map((m) => (
                            <option key={m.id} value={m.name}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="arrow-divider">➔</div>

                      <div className="form-group">
                        <label htmlFor="debt-to">Komu:</label>
                        <select
                          id="debt-to"
                          value={debtTo}
                          onChange={(e) => setDebtTo(e.target.value)}
                          required
                        >
                          {members.map((m) => (
                            <option key={m.id} value={m.name}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="form-group">
                      <label htmlFor="debt-amount">Kwota (zł):</label>
                      <input
                        type="number"
                        id="debt-amount"
                        step="0.01"
                        min="0.01"
                        placeholder="np. 45.50"
                        value={debtAmount}
                        onChange={(e) => setDebtAmount(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="debt-title">Tytułem (opcjonalnie):</label>
                      <input
                        type="text"
                        id="debt-title"
                        placeholder="np. Za pizzę, Ubera"
                        value={debtTitle}
                        onChange={(e) => setDebtTitle(e.target.value)}
                      />
                    </div>

                    <button type="submit" className="btn btn-primary full-btn">
                      Zapisz rozliczenie
                    </button>
                  </form>
                )}
              </section>

              {/* Podsumowanie sald po zbilansowaniu */}
              <section className="box full-width">
                <h2>Podsumowanie sald (kto komu łącznie oddaje)</h2>
                {summary.length === 0 ? (
                  <p className="empty-text">
                    Wszystko rozliczone — brak aktywnych zobowiązań w grupie.
                  </p>
                ) : (
                  <ul className="custom-list">
                    {summary.map((item, idx) => (
                      <li key={idx} className="debt-item">
                        <div className="debt-info">
                          <strong>{item.debt_from}</strong> ➔{" "}
                          <strong>{item.debt_to}</strong>
                        </div>
                        <div className="debt-actions">
                          <span className="amount-tag summary-amount">
                            {Number(item.amount).toFixed(2)} zł
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* Historia i bieżące zobowiązania */}
              <section className="box full-width">
                <h2>Historia i bieżące zobowiązania</h2>
                <div id="debts-container">
                  {debts.length === 0 ? (
                    <p className="empty-text">
                      Brak zapisanych rozliczeń w tej grupie.
                    </p>
                  ) : (
                    <ul id="debts-list" className="custom-list">
                      {debts.map((d) => (
                        <li
                          key={d.id}
                          className={`debt-item ${d.is_settled ? "settled" : ""}`}
                        >
                          <div className="debt-info">
                            <strong>{d.debt_from}</strong> ma oddać{" "}
                            <strong>{d.debt_to}</strong>
                            {d.title && (
                              <span className="debt-title-tag">{d.title}</span>
                            )}
                            {Boolean(d.is_settled) && (
                              <span className="settled-badge">Rozliczone</span>
                            )}
                          </div>

                          <div className="debt-actions">
                            <span className="amount-tag">
                              {Number(d.amount).toFixed(2)} zł
                            </span>

                            {!d.is_settled ? (
                              <>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline"
                                  onClick={() =>
                                    setEditingDebt({
                                      ...d,
                                      amount: String(d.amount),
                                    })
                                  }
                                >
                                  Edytuj
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-danger-text"
                                  onClick={() => handleToggleSettle(d.id)}
                                >
                                  Rozliczone
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline"
                                  onClick={() => handleToggleSettle(d.id)}
                                >
                                  Cofnij
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-danger-text"
                                  onClick={() => handleDeleteDebt(d.id)}
                                >
                                  Usuń
                                </button>
                              </>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </main>

      {/* Modal tworzenia nowej grupy */}
      {showGroupModal && (
        <div
          className="modal-overlay"
          onClick={() => setShowGroupModal(false)}
        >
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h2>Nowa grupa</h2>
            <form onSubmit={handleCreateGroup}>
              <div className="form-group">
                <label htmlFor="modal-group-name">Nazwa grupy:</label>
                <input
                  id="modal-group-name"
                  type="text"
                  placeholder="np. Wyjście na miasto, Wyjazd w góry"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowGroupModal(false)}
                >
                  Anuluj
                </button>
                <button type="submit" className="btn btn-primary">
                  Utwórz
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal edycji istniejącego rozliczenia */}
      {editingDebt && (
        <div className="modal-overlay" onClick={() => setEditingDebt(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h2>Edytuj rozliczenie</h2>
            <form onSubmit={handleSaveEditDebt}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="edit-debt-from">Kto oddaje:</label>
                  <select
                    id="edit-debt-from"
                    value={editingDebt.debt_from}
                    onChange={(e) =>
                      setEditingDebt({
                        ...editingDebt,
                        debt_from: e.target.value,
                      })
                    }
                  >
                    {editPeopleOptions.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="arrow-divider">➔</div>

                <div className="form-group">
                  <label htmlFor="edit-debt-to">Komu:</label>
                  <select
                    id="edit-debt-to"
                    value={editingDebt.debt_to}
                    onChange={(e) =>
                      setEditingDebt({
                        ...editingDebt,
                        debt_to: e.target.value,
                      })
                    }
                  >
                    {editPeopleOptions.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="edit-debt-amount">Kwota (zł):</label>
                <input
                  id="edit-debt-amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={editingDebt.amount}
                  onChange={(e) =>
                    setEditingDebt({ ...editingDebt, amount: e.target.value })
                  }
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="edit-debt-title">Tytułem (opcjonalnie):</label>
                <input
                  id="edit-debt-title"
                  type="text"
                  value={editingDebt.title || ""}
                  onChange={(e) =>
                    setEditingDebt({ ...editingDebt, title: e.target.value })
                  }
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setEditingDebt(null)}
                >
                  Anuluj
                </button>
                <button type="submit" className="btn btn-primary">
                  Zapisz zmiany
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
