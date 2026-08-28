const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function Home() {
  return (
    <main>
      <p className="eyebrow">Private wealth workspace</p>
      <h1>Personal Portfolio Intelligence</h1>
      <p>The application foundation is ready. Personal-finance tools are the first module.</p>
      <p className="connection">Frontend → {apiUrl} → PostgreSQL</p>
    </main>
  );
}
