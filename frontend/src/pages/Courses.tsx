import { useState, useEffect, type FormEvent } from 'react';
import { apiFetch } from '../api';

export interface CourseDetail {
  id: number;
  code: string;
  title: string;
  credits: number;
  level: number;
  prerequisites: string;
  corequisites: string[];
  offerings: string[];
  prereq_manual_review?: boolean;
}

export default function Courses() {
  const [searchTerm, setSearchTerm] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [courses, setCourses] = useState<CourseDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchCourses(query: string) {
    setLoading(true);
    setError(null);
    try {
      const url = query.trim() ? `/api/courses/?q=${encodeURIComponent(query.trim())}` : '/api/courses/';
      const data = await apiFetch<{ results: CourseDetail[] }>(url);
      setCourses(data?.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search courses');
      setCourses([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCourses('');
  }, []);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setSubmittedQuery(searchTerm);
    fetchCourses(searchTerm);
  }

  function handleClear() {
    setSearchTerm('');
    setSubmittedQuery('');
    fetchCourses('');
  }

  return (
    <main className="auth-card profile-card" style={{ maxWidth: '900px' }}>
      <h1>Course Catalog</h1>
      <p style={{ color: 'var(--muted)', marginTop: '0.25rem' }}>
        Search courses by code or title to review credits, terms offered, and prerequisite/corequisite constraints.
      </p>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', marginTop: '1.25rem', marginBottom: '1.5rem' }}>
        <input
          type="search"
          placeholder="Search by course code or title (e.g. algorithms)..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            flex: 1,
            padding: '0.6rem 0.8rem',
            borderRadius: '8px',
            border: '1px solid var(--line)',
            fontSize: '1rem'
          }}
          aria-label="Search courses"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
        {searchTerm && (
          <button type="button" onClick={handleClear} className="btn-secondary">
            Clear
          </button>
        )}
      </form>

      {error && (
        <div role="alert" className="form-error" style={{ marginBottom: '1rem' }}>
          <p>{error}</p>
        </div>
      )}

      {loading && <p style={{ color: 'var(--muted)', padding: '1rem 0' }}>Loading courses…</p>}

      {!loading && courses.length === 0 && (
        <div role="status" style={{ padding: '2rem 1rem', textAlign: 'center', background: 'var(--violet-50)', borderRadius: '8px' }}>
          <p style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--violet-dark)', margin: 0 }}>
            No courses found
          </p>
          {submittedQuery && (
            <p style={{ color: 'var(--muted)', marginTop: '0.5rem', marginBottom: 0 }}>
              No catalog offerings match "{submittedQuery}". Try checking for typos or searching a broader term.
            </p>
          )}
        </div>
      )}

      {!loading && courses.length > 0 && (
        <section aria-label="Search results">
          <p style={{ fontSize: '0.9rem', color: 'var(--muted)', marginBottom: '0.75rem' }}>
            Showing {courses.length} course{courses.length === 1 ? '' : 's'}
          </p>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {courses.map((course) => (
              <li
                key={course.code}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: '8px',
                  padding: '1rem',
                  background: '#fff'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1.15rem' }}>
                    <span style={{ color: 'var(--violet)', fontWeight: 700 }}>{course.code}</span> — {course.title}
                  </h3>
                  <span style={{ background: 'var(--violet-100)', color: 'var(--violet-dark)', padding: '0.2rem 0.55rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 600 }}>
                    {course.credits} credit{course.credits === 1 ? '' : 's'}
                  </span>
                </div>

                <div style={{ marginTop: '0.6rem', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  <div>
                    <strong>Terms Offered: </strong>
                    {course.offerings && course.offerings.length > 0 ? (
                      course.offerings.map((term) => (
                        <span
                          key={term}
                          style={{
                            display: 'inline-block',
                            marginRight: '0.35rem',
                            padding: '0.1rem 0.45rem',
                            background: '#f4f4f5',
                            border: '1px solid #e4e4e7',
                            borderRadius: '4px',
                            fontSize: '0.8rem'
                          }}
                        >
                          {term}
                        </span>
                      ))
                    ) : (
                      <span style={{ color: 'var(--muted)' }}>Not specified</span>
                    )}
                  </div>

                  <div>
                    <strong>Prerequisites: </strong>
                    {course.prerequisites ? (
                      <span style={{ fontFamily: 'monospace', color: 'var(--violet-dark)', background: 'var(--violet-50)', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                        {course.prerequisites}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--muted)' }}>None</span>
                    )}
                    {course.prereq_manual_review && (
                      <span style={{ marginLeft: '0.5rem', color: '#b45309', fontSize: '0.8rem', fontStyle: 'italic' }}>
                        (Requires departmental manual review)
                      </span>
                    )}
                  </div>

                  <div>
                    <strong>Corequisites: </strong>
                    {course.corequisites && course.corequisites.length > 0 ? (
                      <span style={{ fontFamily: 'monospace', color: 'var(--violet-dark)' }}>
                        {course.corequisites.join(', ')}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--muted)' }}>None</span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
