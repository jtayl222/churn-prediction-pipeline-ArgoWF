# Managing your technical writing workflow alongside your code projects

**Where to Store Article Drafts:**

1.  **Within the Relevant Git Repository (Recommended for Project-Specific Articles):**
    *   **Pros:**
        *   **Colocation:** The article lives with the code it describes. This makes it easy to keep them in sync. If you update the code, the article is right there to be updated too.
        *   **Version Control:** Just like your code, your article drafts benefit from Git's version history, branching, and diffing. You can see how an article evolved.
        *   **Collaboration (if applicable):** If others contribute to the project, they can also contribute to or review the article using standard Git workflows (pull requests).
        *   **Discoverability:** Someone browsing your project on GitHub can easily find the accompanying article or tutorial.
    *   **Cons:**
        *   Can slightly "clutter" a purely code-focused repository if you have many articles or very large ones with many assets.
    *   **How to do it:**
        *   Create a `docs/articles/` directory, or simply a top-level `articles/` directory in the repo.
        *   Store drafts in Markdown (`.md`).
        *   Include any images or assets for the article in a subdirectory (e.g., `articles/my-article-title/images/`).
        *   Link to the published article from your project's main README.md.

2.  **A Dedicated "Blog" or "Content" Git Repository:**
    *   **Pros:**
        *   **Centralization:** All your articles, regardless of the specific code project they relate to, are in one place.
        *   **Clean Separation:** Keeps your code repositories focused purely on code.
        *   **Easier to Build a Static Site:** If you decide to host your own blog using a static site generator (like Hugo, Jekyll, Next.js, Docusaurus), having all content in one repo is ideal.
    *   **Cons:**
        *   Slightly harder to keep articles perfectly in sync with code changes in separate repositories. You'll need a good process.
    *   **How to do it:**
        *   Create a new Git repository (e.g., `my-tech-blog-content`).
        *   Organize articles in subdirectories, perhaps by topic or date.

**Which to choose?**

*   If an article is **tightly coupled** to a specific project (e.g., "How to run my `churn-prediction-pipeline-ArgoWF` project"), store it **within that project's repo.**
*   If you're writing more **general MLOps articles** that draw on experiences from multiple projects, or if you plan to build a personal tech blog, a **dedicated content repository** is a good idea.
*   You can also do a hybrid: project-specific tutorials in their repos, and more general thought pieces in a central blog repo.

**Where to Publish (Beyond Medium.com):**

Medium is a good platform for reach, but you have other excellent options, especially for building a personal brand and demonstrating technical depth:

1.  **Your Own Static Site/Blog (Highly Recommended for MLOps Engineers):**
    *   **Platforms:**
        *   **GitHub Pages with Jekyll or Hugo:** Free, integrates directly with Git, highly customizable. Hugo is very fast and popular.
        *   **Docusaurus:** Excellent for technical documentation and blogs, built by Facebook. Great for code highlighting and versioning docs.
        *   **Next.js/Gatsby:** More powerful React-based frameworks if you want a highly dynamic or app-like blog.
        *   **Quartz.jz.org:** A new, promising option for digital gardens/second brains, also Markdown-based.
    *   **Pros:**
        *   **Full Ownership & Control:** Your content, your domain, your design. No platform risk.
        *   **Demonstrates Technical Skills:** Setting up and maintaining your own blog (especially if deployed via CI/CD from your Git repo) is a mini-project in itself that showcases relevant skills.
        *   **SEO Benefits:** You build SEO for your own domain.
        *   **Customization:** Tailor it exactly to your needs.
        *   **Can integrate with your Git workflow seamlessly.**
    *   **Cons:**
        *   More initial setup effort.
        *   You're responsible for driving traffic (though you can still syndicate to Medium).

2.  **Dev.to:**
    *   **Pros:** Large, engaged developer community. Good for visibility and feedback. Markdown-based.
    *   **Cons:** Platform-owned.

3.  **Hashnode:**
    *   **Pros:** Allows you to blog on your own custom domain while leveraging their platform features. Good developer focus. Markdown-based.
    *   **Cons:** Still a platform, though with more ownership features than Medium.

4.  **Company Tech Blogs (Guest Posting):**
    *   **Pros:** Reach a new audience, associate yourself with a known brand.
    *   **Cons:** Less control, need to find opportunities.

5.  **LinkedIn Articles:**
    *   **Pros:** Good for professional networking and visibility within your existing network.
    *   **Cons:** Limited formatting, content lives on LinkedIn.

**Recommendation for You:**

*   **Store drafts in Markdown within the relevant Git repository** for project-specific articles.
*   **Consider setting up your own static site blog using GitHub Pages with Hugo or Docusaurus.** This is a fantastic way to showcase your technical skills and own your content. You can then:
    *   Publish primarily to your own blog.
    *   **Syndicate** (re-publish with a canonical link pointing back to your original) your articles to Medium, Dev.to, or Hashnode for broader reach. This is a common and accepted practice.
*   This combination gives you ownership, technical credibility, and the reach of larger platforms.

By managing your article drafts in Git and potentially hosting your own blog, you're treating your technical writing with the same rigor as your code, which is a great habit for an MLOps engineer.