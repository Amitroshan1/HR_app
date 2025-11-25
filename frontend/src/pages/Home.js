import "./Home.css";

function Home() {
  return (
    <div className="hero-section">

      <div className="hero-content fade-in">

        <h1 className="hero-title">Welcome...</h1>

        <h2 className="hero-subtitle">
          Unlock Your Potential with our Innovative Platform.
          <br /><br />
          Streamline Your Processes and Enhance Team Productivity.
          <br /><br />
          Ready to get started?
        </h2>

        <h3 className="hero-small-text">Please Login to Continue...</h3>

        <a
          href="http://localhost:5000/login"
          className="hero-btn"
        >
          Login with Microsoft
        </a>

      </div>

      {/* Decorative wave background */}
      <div className="hero-wave"></div>

    </div>
  );
}

export default Home;
