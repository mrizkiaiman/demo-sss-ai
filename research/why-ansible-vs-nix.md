# Research: why Ansible for SSS

**Checked:** 2026-10-08  
**Question:** Why use Ansible for the SSS proof of concept, how does it compare with the existing Nix approach, and why not use other configuration tools?

## Recommendation

Use Ansible for this PoC because SSS currently distributes skill files, merges MCP entries into several existing application config files, previews the proposed changes, and applies them on developer workstations. Ansible already provides file and template modules, check mode, diff output, and change reporting for this configuration-management workflow. The repository also has a launcher and checks around these behaviors. This is a fit for the current scope, not a claim that Ansible is universally better than Nix.

Choose Nix instead if the objective expands to reproducibly installing and pinning the broader developer toolchain, managing packages and shell environments, and activating or rolling back complete user environments. Those are Nix's strengths and are closer to the broader `sss-ai-nix` design.

## Fit to the current SSS scope

| Need | Ansible fit in this repository | Relevant capability or limit |
|---|---|---|
| Put selected skill files in client-specific locations | The skills role validates selections and installs the chosen package files. | Ansible `copy` and `file` modules manage files and their state. See [skills role](../ansible/roles/ai/skills/tasks/main.yml) and [Ansible copy module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/copy_module.html). |
| Update several MCP file formats while retaining unrelated settings | The repo has a filter for JSON, JSON5, and TOML that updates managed entries while leaving other entries in place. | This is repo-specific merge logic, not an automatic Ansible feature. See [MCP filter](../ansible/filter_plugins/mcp_config.py). |
| Preview and confirm changes | The launcher runs Ansible check mode and asks before applying. | Ansible check mode simulates tasks and diff mode shows changes for modules that support them. Check mode is not a perfect simulation for every task or module. See [launcher](../ansible/scripts/configure.py) and [check and diff modes](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html). |
| Report whether files changed and create backups | The MCP role backs up existing files when writing changed content. The file modules report changes. | The template module documents `backup`, check-mode, and diff-mode support. See [MCP role](../ansible/roles/ai/mcp/tasks/main.yml) and [template module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html). |
| Configure the current workstation | The default inventory targets `localhost` with a local connection. | Ansible supports local connection plugins as well as remote connections. The current PoC does not need a controller service or SSH fleet. See [local inventory](../ansible/inventories/local/hosts.yml) and [connection details](https://docs.ansible.com/projects/ansible/latest/user_guide/connection_details.html). |

The main reason to select Ansible is therefore operational fit: the current deliverable is a previewable configuration deployment with explicit file-level behavior. Ansible's changed reporting also gives the PoC a direct way to check repeat runs, while the repository's own merge filter and checks handle client-specific details.

## Ansible compared with Nix

| Dimension | Ansible SSS | Nix SSS (`sss-ai-nix`) |
|---|---|---|
| Best fit | Apply selected files and settings to a workstation. | Describe and activate a reproducible user environment, including packages and shell tools. |
| Setup burden | Python, Git, and Ansible dependencies; no Nix installation is required. | Requires Nix with flakes enabled plus Home Manager. The repo bootstrap installs Nix when absent. |
| Configuration model | Tasks inspect and update destination files. The MCP role merges managed entries into existing JSON/JSON5/TOML settings. | Home Manager evaluates a declared profile and links generated files from the Nix store into the home directory. The current MCP module writes a complete shared JSON object to its destinations, so it needs review before use where developers have existing MCP entries. |
| Preview and repeatability | Check/diff preview; unchanged resources should report no change when tasks support check mode and are idempotent. | Flake inputs are locked, and Nix builds immutable store outputs. `home-manager switch` activates a generation. |
| Rollback | MCP file backups are available for changed files; restoring means using the backup or applying a corrected configuration. | Home Manager maintains generations that can be selected for rollback. |
| Scope in current repo | Five AI coding clients, skills, and MCP. | Broader toolchain, shell, packages, agent configs, security files, and AI settings are described in its README and modules. |
| Practical tradeoff | Simpler for this file-configuration PoC, but custom merge behavior must be maintained and tested. | Better when full environment reproducibility is a requirement, but Nix and Home Manager increase onboarding and operational complexity for a pilot that mainly edits client config files. |

The two repositories have different scopes. The Nix repository describes a broader developer platform, while the Ansible repository focuses on installing shared skills and configuring MCP across the five clients. Keep that distinction explicit in a decision document. Nix is not rejected for technical inability; it is a larger platform choice than this PoC currently needs.

Internal implementation references: [Ansible README](../README.md), [Ansible setup playbook](../ansible/setup.yml), [Nix README](../../sss-ai-nix/README.md), [Nix flake](../../sss-ai-nix/flake.nix), [Nix skills module](../../sss-ai-nix/modules/skills/default.nix), [Nix MCP module](../../sss-ai-nix/modules/mcp/default.nix), and [Nix bootstrap](../../sss-ai-nix/scripts/install-nix.sh).

## Why not other tools?

| Alternative | What it does well | Why it was not selected for this PoC |
|---|---|---|
| Shell scripts | Minimal dependencies and direct control over local files. | SSS needs selection, format-aware merging, previews, backups, validation, and reliable repeat runs. A script-based implementation would need to build and maintain these behaviors itself. The launcher still uses Python for its menu, so Ansible is not eliminating every runtime dependency; it supplies the deployment model and modules. |
| chezmoi | Purpose-built for managing dotfiles across machines. It supports templates, diffs, apply workflows, and scripts. | It is a credible alternative, especially if SSS becomes a dotfile-management project. The current Ansible roles already express the deployment and backup behavior, and the MCP format conversion/merge logic is already implemented there. Choosing chezmoi would mean moving this behavior into its templates/scripts or another helper and validating the same client-specific cases. |
| GNU Stow | Simple package-to-home-directory symlinks, with install and uninstall operations. | SSS must merge structured MCP data and validate distinct client schemas. Stow's core model is symlink management, so it does not cover those requirements by itself. |
| Nix + Home Manager | Strong reproducibility, pinned inputs, declarative package and user-environment management, and generation-based activation. | Use it if those broader environment goals are in scope. For the current PoC, Nix adds a dedicated package manager and Home Manager to a workflow focused on client configuration files. The current Nix MCP module also replaces the destination JSON payload rather than merging into an existing developer config, so it would need additional implementation and verification for safe coexistence. |

These alternatives are not incapable in general. The decision is based on the current PoC's target, existing implementation, onboarding requirements, and the behavior that must be demonstrated.

## Opsi pengelolaan konfigurasi jarak jauh

Jika jumlah workstation developer bertambah dan tim perlu menerapkan konfigurasi SSS secara terpusat, Ansible dapat dievaluasi sebagai kemampuan operasional tahap berikutnya. Opsi ini belum diperlukan untuk PoC saat ini yang menargetkan workstation lokal, tetapi dapat menjadi jalur untuk memperluas workflow konfigurasi yang sama.

- **Controller terpusat:** Workstation admin, CI runner, atau layanan otomasi dapat mengambil revision repository SSS yang sudah ditentukan, menyimpan inventory workstation, dan menjalankan playbook ke machine yang dipilih. Developer tidak perlu melakukan pull repository dan menerapkan konfigurasi secara manual.
- **Operasi bersama:** Playbook yang sama dapat digunakan untuk onboarding, update rutin, dan perbaikan konfigurasi pada beberapa workstation. Group dalam inventory dapat menentukan konfigurasi yang diterapkan ke workstation atau tim tertentu.
- **Pelaporan eksekusi:** Ansible melaporkan hasil task untuk setiap host. Callback plugin atau integrasi CI dapat menyimpan output dan mengidentifikasi workstation yang berhasil, berubah, tidak dapat dihubungi, atau gagal sehingga tim dapat menindaklanjuti pengecualian.
- **Prasyarat:** Controller memerlukan koneksi jaringan, akses remote yang terautentikasi, izin sesuai prinsip least privilege, dan inventory yang selalu diperbarui. Credential serta variable sensitif harus disimpan di secret manager atau mekanisme terlindungi yang setara, bukan di dalam playbook.
- **Pertimbangan operasional:** Tim perlu menentukan strategi rollout, retry, dan penanganan workstation yang sedang offline, serta melindungi controller, credential, dan log eksekusi. CLI atau CI runner sudah cukup untuk rollout awal; AWX atau Ansible Automation Platform dapat dievaluasi kemudian jika tim memerlukan UI, penjadwalan, role-based access, atau audit history terpusat.

Penilaian terhadap kebutuhan saat ini menggunakan weighted decision matrix dengan skala 1–5:

| Kriteria | Bobot | Ansible | Nix / NixOS + Colmena |
|---|---:|---:|---:|
| Biaya | 20% | 4 | 4 |
| Keamanan | 25% | 4 | 4 |
| Kemudahan instalasi | 20% | 5 | 2 |
| Kesesuaian kebutuhan | 20% | 5 | 4 |
| Pemeliharaan | 10% | 4 | 5 |
| Kemudahan adopsi tim | 5% | 5 | 2 |
| **Skor akhir** | **100%** | **4,45 / 5** | **3,60 / 5** |

Skor ini menunjukkan bahwa Ansible lebih sesuai untuk kebutuhan saat ini: menerapkan file skills dan konfigurasi MCP ke workstation yang sudah ada, menjalankan onboarding atau update secara terpusat, serta mendukung kemungkinan environment yang heterogen. Nix tetap lebih menarik jika scope berkembang menjadi pengelolaan toolchain dan user environment Linux yang reproducible, deklaratif, serta memiliki rollback berbasis generation. Skor Nix di atas mengacu pada NixOS + Colmena, bukan sekadar instalasi Nix package manager di Ubuntu atau macOS.

### Cara membaca perbandingan biaya

Skor biaya tidak hanya membandingkan harga lisensi. Keduanya open source, sehingga biaya utama berasal dari instalasi awal, waktu belajar, infrastruktur controller atau build, dan effort pemeliharaan.

- **Biaya awal Ansible lebih rendah:** Ansible dapat dipasang di satu controller tanpa mengganti sistem operasi workstation. Target biasanya hanya memerlukan koneksi remote, credential, dan Python atau runtime yang sesuai. Workstation yang sudah memakai Ubuntu, macOS, atau OS lain tetap dapat dipertahankan.
- **Biaya awal Nix lebih tinggi:** Tim perlu memasang Nix dan menyiapkan flakes, module, serta Home Manager. Jika menggunakan NixOS, migrasi atau provisioning sistem menjadi bagian dari pekerjaan. Untuk deployment yang lebih besar, tim mungkin juga memerlukan binary cache atau CI untuk membangun konfigurasi secara konsisten.
- **Biaya setelah stabil berbeda:** Ansible tetap memerlukan pemeliharaan inventory, credential, perbedaan antar-OS, dan playbook. Nix dapat mengurangi sebagian effort tersebut karena konfigurasi, package, dan dependency dideklarasikan dalam satu flake yang dapat direproduksi. Namun, Nix tetap memerlukan pemeliharaan flake, input yang di-lock, dan pemahaman khusus dari tim.

Contoh untuk 10 workstation developer:

- Dengan Ansible, controller menyimpan satu inventory dan playbook. Tim dapat menjalankan satu deployment untuk menyalin skills, memperbarui konfigurasi MCP, dan melakukan onboarding ke workstation yang sudah ada. Biaya terbesar setelahnya adalah menjaga inventory, akses remote, dan compatibility antar-OS.
- Dengan Nix, tim perlu menyiapkan Nix atau NixOS, Home Manager, dan flake pada workstation tersebut terlebih dahulu. Setelah setup selesai, workstation baru dapat menggunakan deklarasi yang sama, dependency lebih konsisten, dan rollback generation tersedia. Manfaat ini lebih besar jika tim juga ingin mengelola package, shell, dan toolchain secara keseluruhan.
- Jika scope hanya menyalin beberapa file skills dan menggabungkan konfigurasi MCP, tambahan layer Nix belum tentu menghemat biaya. Dalam scope tersebut, effort instalasi dan adopsi Nix dapat lebih besar daripada effort pemeliharaan playbook Ansible.

Jadi, pernyataan bahwa Ansible lebih murah untuk mulai berarti **barrier awal dan perubahan pada workstation lebih kecil**, bukan berarti Ansible selalu memiliki total biaya terendah. Nix dapat menjadi lebih efisien setelah platformnya stabil dan scope membutuhkan reproducibility penuh, tetapi tidak otomatis lebih murah untuk workflow konfigurasi file yang sederhana.

## Keputusan dan catatan

- **Keputusan PoC:** Tetap gunakan Ansible sebagai apply engine untuk skills workstation dan pengaturan MCP. Python launcher yang ada tetap digunakan untuk pemilihan dan konfirmasi.
- **Tahap berikutnya:** Evaluasi remote configuration management jika jumlah workstation bertambah atau tim membutuhkan onboarding, update, dan remediation dari satu controller.
- **Evaluasi ulang Nix:** Pertimbangkan Nix jika scope yang disetujui mencakup pinning atau instalasi toolchain bersama, pengelolaan shell dan package state yang lebih luas, atau kebutuhan rollback user environment berbasis generation.
- **Batasan check mode:** Jangan menganggap Ansible check mode sebagai bukti perilaku runtime. Mode ini memprediksi perubahan untuk task yang didukung. Setiap AI client yang dipilih tetap memerlukan pemeriksaan aktual untuk skill load dan koneksi MCP.
- **Batasan keamanan:** Jangan menganggap Ansible atau Nix sebagai access-control boundary untuk AI. File permission, network control, dan secret handling tetap harus dikelola sebagai kontrol terpisah.

## Sources

- Ansible: [playbooks and idempotency](https://docs.ansible.com/projects/ansible-core/devel/playbook_guide/playbooks_intro.html), [check and diff modes](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html), [template module backup and mode support](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html), [connection methods](https://docs.ansible.com/projects/ansible/latest/user_guide/connection_details.html).
- Nix: [Nix reference manual](https://nix.dev/manual/nix/2.35/), [flakes and lock files](https://nix.dev/concepts/flakes.html), [Home Manager manual](https://home-manager.dev/manual/unstable/).
- chezmoi: [templates](https://www.chezmoi.io/user-guide/templating/), [scripts](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/), [diff and apply workflow](https://www.chezmoi.io/user-guide/frequently-asked-questions/usage/).
- GNU Stow: [project description](https://www.gnu.org/software/stow/), [manual](https://www.gnu.org/software/stow/manual/stow.html).
