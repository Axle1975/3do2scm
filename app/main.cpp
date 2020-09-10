#include <iostream>
#include <filesystem>
#include <fstream>
#include <map>
#include <list>
#include <set>
#include <memory>
#include <sstream>

#include <rwe/_3do.h>
#include <rwe/Gaf.h>
#include <scm/ScmFile_format.h>

const double SCALE = 65536.0;
static const std::string COLOR_INDEX_NAME_PREFIX("__colorIndex");

std::string GetColorIndexName(unsigned colorIndex)
{
    std::ostringstream ss;
    ss << COLOR_INDEX_NAME_PREFIX << colorIndex;
    return ss.str();
}

bool IsColorIndexName(const std::string& name)
{
    return name.rfind(COLOR_INDEX_NAME_PREFIX, 0) == 0;
}

unsigned GetIndexFromColorIndexName(const std::string& name)
{
    return std::stoi(name.substr(COLOR_INDEX_NAME_PREFIX.size()));
}

std::vector<std::uint32_t> LoadPalette(const std::string &filename)
{
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<std::uint32_t> palette(size/4u);
    file.read((char*)palette.data(), size);

    return palette;
}

void rgb2hsv(std::uint8_t r, std::uint8_t g, std::uint8_t b, double& h, double& s, double& v)
{
    const double epsilon = 1e-6;
    std::int16_t min = std::min(std::min(r,g),b);
    std::int16_t max = std::max(std::max(r, g), b);
    std::int16_t delta = max - min;

    v = max;
    if (delta == 0)
    {
        s = 0.0;
        h = std::numeric_limits<double>::quiet_NaN();
        return;
    }

    if (max > 0) {
        s = double(delta) / double(max);
    }
    else {
        // if max is 0, then r = g = b = 0              
        // s = 0, h is undefined
        s = 0.0;
        h = std::numeric_limits<double>::quiet_NaN();
        return;
    }

    if (r == max)
    {
        h = double(g - b) / double(delta);        // between yellow & magenta
    }
    else
    {
        if (g == max)
        {
            h = 2.0 + double(b - r) / double(delta);  // between cyan & yellow
        }
        else
        {
            h = 4.0 + double(r - g) / double(delta);  // between magenta & cyan
        }
    }

    h *= 60.0;                              // degrees
    if (h < 0.0)
        h += 360.0;
}


class CompositeTexture : public rwe::GafReaderAdapter
{
    const int m_width;
    const int m_height;
    std::shared_ptr<char> m_buffer;
    std::shared_ptr<char> m_occupied;
    std::shared_ptr<char> m_isLogo;
    std::vector<std::uint32_t> m_paletteRgba;

    std::map< std::string, LayerData > m_textures;
    LayerData* m_currentTexture;
    bool m_currentTextureIsLogo;

public:

    class BufferFull : public std::runtime_error
    {
    public:
        BufferFull() :
            std::runtime_error("cannot place texture. buffer full")
        { }
    };

    CompositeTexture(int width, int height, const std::string &colourPalette) :
        m_width(width),
        m_height(height),
        m_buffer(new char[width * height]),
        m_occupied(new char[width * height]),
        m_isLogo(new char[width * height]),
        m_currentTexture(NULL),
        m_currentTextureIsLogo(false)

    {
        std::memset(m_buffer.get(), 0, width * height);
        std::memset(m_occupied.get(), 0, width * height);
        std::memset(m_isLogo.get(), 0, width * height);
        m_paletteRgba = LoadPalette(colourPalette);
    }

    virtual void setCurrentTextureIsLogo(bool isLogo)
    {
        m_currentTextureIsLogo = isLogo;
    }

    virtual void beginEntity(const std::string& name)
    {
        auto it = m_textures.find(name);
        if (it == m_textures.end())
        {
            m_textures[name].data = NULL;
        }

        m_currentTexture = &m_textures[name];
    }

    virtual void beginFrame(const rwe::GafFrameData& header)
    {
        if (m_currentTexture && m_currentTexture->data == NULL)
        {
            m_currentTexture->width = header.width;
            m_currentTexture->height = header.height;
            m_currentTexture->transparencyKey = header.transparencyIndex;
            FindPlacement(*m_currentTexture);
        }
    }

    virtual void frameLayer(const LayerData& data)
    {
        if (m_currentTexture && m_currentTexture->data)
        {
            for (unsigned col = 0; col < m_currentTexture->width; ++col)
            {
                for (unsigned row = 0; row < m_currentTexture->height; ++row)
                {
                    char p = data.data[col + m_currentTexture->width * row];
                    unsigned idxDest = col + m_width * row;
                    if (idxDest + m_currentTexture->x < m_width * m_height)
                    {
                        m_currentTexture->data[col + m_width * row] = p;
                    }
                }
            }
            // keep the first layer only
            m_currentTexture = NULL;
        }
    }

    virtual void addColorIndex(const std::string& colorIndexTextureName)
    {
        if (m_textures.count(colorIndexTextureName) > 0u)
        {
            return;
        }

        int colorIndex = GetIndexFromColorIndexName(colorIndexTextureName);
        auto & tex = m_textures[colorIndexTextureName];
        tex.width = 4;
        tex.height = 4;
        tex.transparencyKey = colorIndex-1u;
        tex.data = NULL;
        m_currentTextureIsLogo = false;

        FindPlacement(tex);   // points tex.data to a free spot

        for (unsigned col = 0; col < tex.width; ++col)
        {
            for (unsigned row = 0; row < tex.height; ++row)
            {
                unsigned idxDest = col + m_width * row;
                if (idxDest + tex.x < m_width * m_height)
                {
                    tex.data[col + m_width * row] = colorIndex;
                }
            }
        }
    }

    virtual void endFrame()
    { }

    virtual void endEntity()
    {
        m_currentTexture = NULL;
    }

    int getWidth() const {
        return m_width;
    }
    int getHeight() const {
        return m_height;
    }

    void colourLookup(std::uint8_t index, std::uint8_t& r, std::uint8_t& g, std::uint8_t& b) const
    {
        struct RGBA
        {
            std::uint8_t r;
            std::uint8_t g;
            std::uint8_t b;
            std::uint8_t a;
        };
        union {
            RGBA rgba;
            std::uint32_t _word;
        } word;

        word._word = m_paletteRgba[index];
        r = word.rgba.r;
        g = word.rgba.g;
        b = word.rgba.b;
    }

    void saveTextures(std::ostream& os) const
    {
        // raw colour indexed
        // raw rgba
        for (unsigned idx = 0u; idx < m_width * m_height; ++idx)
        {
            std::uint8_t r, g, b;
            double h, s, v;
            colourLookup(m_buffer.get()[idx], r, g, b);
            rgb2hsv(r, g, b, h, s, v);
            bool isLogoPixel = this->m_isLogo.get()[idx] && s > 0.333;

            if (isLogoPixel)
            {
                r = g = b = 0u;
            }
            os.put(r);
            os.put(g);
            os.put(b);
            os.put(255);
        }
    }

    void saveLogos(std::ostream& os) const
    {
        // raw rgba
        for (unsigned idx = 0u; idx < m_width * m_height; ++idx)
        {
            std::uint8_t r, g, b;
            double h, s, v;
            colourLookup(m_buffer.get()[idx], r, g, b);
            rgb2hsv(r, g, b, h, s, v);
            bool isLogoPixel = this->m_isLogo.get()[idx] && s > 0.333;

            os.put(0);
            os.put(0);
            os.put(0);
            os.put(isLogoPixel ? 255-char(255.0*v) : 0);
        }
    }

    void getTextureUV(const std::string& name, double uvMin[2], double uvMax[2]) const
    {
        auto it = m_textures.find(name);
        if (it == m_textures.end())
        {
            uvMin[0] = uvMin[1] = uvMax[0] = uvMax[1] = 0.0;
            std::cerr << "unknown texture: '" << name << "'" << std::endl;
            return;
        }

        const LayerData& tex = it->second;
        uvMin[0] = double(tex.x) / double(m_width);
        uvMin[1] = double(tex.y) / double(m_height);
        uvMax[0] = double(tex.x+tex.width) / double(m_width);
        uvMax[1] = double(tex.y+tex.height) / double(m_height);
    }

private:
    bool IsOccupied(const LayerData& tex, bool markOccupied)
    {
        for (unsigned int col = 0; col < tex.width; ++col)
        {
            for (unsigned int row = 0; row < tex.height; ++row)
            {
                unsigned int idx = tex.x + col + (tex.y + row) * m_width;
                if (markOccupied)
                {
                    m_occupied.get()[idx] = true;
                    m_isLogo.get()[idx] = m_currentTextureIsLogo;
                }
                else if (idx >= m_width * m_height || m_occupied.get()[idx])
                {
                    return true;
                }
            }
        }
        return false;
    }

    void FindPlacement(LayerData& tex)
    {
        for (tex.x = 0; tex.x+tex.width <= m_width; ++tex.x)
        {
            for (tex.y = 0; tex.y+tex.height <= m_height; ++tex.y)
            {
                if (!IsOccupied(tex,false))
                {
                    tex.data = m_buffer.get() + tex.x + tex.y * m_width;
                    IsOccupied(tex, true);
                    return;
                }
            }
        }
        throw BufferFull();
    }

};

std::string JsonKey(const std::string& k)
{
    const std::string qt("\"");
    return qt + k + qt + ":";
}

void ToJson(std::ostream& os, const rwe::_3do::Vertex& vert)
{
    os << '{' 
        << JsonKey("x") << double(vert.x) / SCALE << ','
        << JsonKey("y") << double(vert.y) / SCALE << ','
        << JsonKey("z") << double(vert.z) / SCALE << '}';
}

void ToJson(std::ostream& os, const rwe::_3do::Primitive& prim, const CompositeTexture& textures)
{
    double uvMin[2] = { 0.0,0.0 }, uvMax[2] = { 0.0,0.0 };

    os << '{';
    if (prim.colorIndex)
    {
        const std::string colorIndexTextureName = GetColorIndexName(*prim.colorIndex);
        os << JsonKey("colorIndex") << *prim.colorIndex << ',';
        os << JsonKey("colorIndexTextureName") << '"' << colorIndexTextureName << '"' << ',';
        textures.getTextureUV(colorIndexTextureName, uvMin, uvMax);
    }
    if (prim.textureName)
    {
        textures.getTextureUV(*prim.textureName, uvMin, uvMax);
        os << JsonKey("textureName") << '"' << *prim.textureName << '"' << ',';
    }
    os << JsonKey("vertices") << '[';
    for (const unsigned int &idx : prim.vertices)
    {
        os << idx;
        if (&idx != &prim.vertices.back())
        {
            os << ',';
        }
    }
    os << "],";

    os << JsonKey("uvmin") << '[' << uvMin[0] << ',' << uvMin[1] << "],";
    os << JsonKey("uvmax") << '[' << uvMax[0] << ',' << uvMax[1] << "]}";
}

void ToJson(std::ostream& os, const rwe::_3do::Object& obj, const CompositeTexture &textures)
{
    os << "{";
    os << JsonKey("x") << double(obj.x) / SCALE << ','
       << JsonKey("y") << double(obj.y) / SCALE << ','
       << JsonKey("z") << double(obj.z) / SCALE << ',';
    os << JsonKey("name") << '"' << obj.name << '"' << ',';
    if (obj.selectionPrimitiveIndex)
    {
        os << JsonKey("selectionPrimitiveIndex") << *obj.selectionPrimitiveIndex << ',';
    }
    os << JsonKey("vertices") << '[';
    for (const rwe::_3do::Vertex &vert : obj.vertices)
    {
        ToJson(os, vert);
        if (&vert != &obj.vertices.back())
        {
            os << ',';
        }
    }
    os << "],";
    os << JsonKey("primitives") << '[';
    for (const rwe::_3do::Primitive& prim : obj.primitives)
    {
        ToJson(os, prim, textures);
        if (&prim != &obj.primitives.back())
        {
            os << ',';
        }
    }
    os << "],";
    os << JsonKey("children") << '[';
    for (const rwe::_3do::Object& child : obj.children)
    {
        ToJson(os, child, textures);
        if (&child != &obj.children.back())
        {
            os << ',';
        }
    }
    os << "]}";
}


void GetAllTextureNames(const rwe::_3do::Object& obj, std::set<std::string> &accumulator)
{
    for (const auto &prim : obj.primitives)
    {
        if (prim.textureName)
        {
            accumulator.insert(*prim.textureName);
        }
        else if (prim.colorIndex)
        {
            accumulator.insert(GetColorIndexName(*prim.colorIndex));
        }
    }

    for (const auto& child : obj.children)
    {
        GetAllTextureNames(child, accumulator);
    }
}


std::shared_ptr<CompositeTexture> MakeTextures(const rwe::_3do::Object& obj, const std::vector<std::string> &taDataDirs)
{
    std::set<std::string> allTextures;
    GetAllTextureNames(obj, allTextures);

    std::list< std::shared_ptr<std::ifstream> > filestreams;
    std::list< std::shared_ptr<rwe::GafArchive> > gafs;
    std::map< std::string, std::shared_ptr<rwe::GafArchive> > gafByTextureName;

    for (const std::string tadata : taDataDirs)
    {
        const std::string directory = tadata + "\\textures";
        for (const auto& dirEntry : std::filesystem::recursive_directory_iterator(directory))
        {
            if (!dirEntry.is_regular_file())
            {
                continue;
            }
            std::shared_ptr<std::ifstream> fs(new std::ifstream(dirEntry, std::ios_base::binary));
            if (fs->good())
            {
                std::shared_ptr<rwe::GafArchive> gaf(new rwe::GafArchive(fs.get(), dirEntry.path().string()));

                for (const rwe::GafArchive::Entry& entry : gaf->entries())
                {
                    if (allTextures.count(entry.name)>0 && gafByTextureName.count(entry.name)==0u)
                    {
                        //std::cerr << "found texture:" << dirEntry << '/' << entry.name << std::endl;
                        gafByTextureName[entry.name] = gaf;
                    }
                }

                filestreams.push_back(fs);
                gafs.push_back(gaf);
            }
        }
    }

    std::filesystem::path palettesFile;
    for (const std::string tadata : taDataDirs)
    {
        std::filesystem::path candidate = std::filesystem::path(tadata) / "palettes" / "PALETTE.PAL";
        if (std::filesystem::exists(candidate))
        {
            //std::cerr << "Found palette file: " << candidate.string() << std::endl;
            palettesFile = candidate;
            break;
        }
    }
    if (!std::filesystem::exists(palettesFile))
    {
        throw std::runtime_error("Unable to find PALETTE.PAL");
    }

    for (int szx = 64; szx <= 2048; szx *= 2)
    {
        for (int szy = szx; szy <= 2 * szx; szy *= 2)
        {
            try
            {
                std::shared_ptr<CompositeTexture> textures(new CompositeTexture(szx, szy, palettesFile.string()));
                for (const auto& tex : allTextures)
                {
                    auto it = gafByTextureName.find(tex);
                    if (it != gafByTextureName.end())
                    {
                        // valid texture
                        auto entry = it->second->findEntry(tex);
                        if (entry)
                        {
                            textures->beginEntity(tex);

                            // not sure how to correctly determine whether or not a gaf should be coloured by team colour.
                            // we'll just make all gafs found in logos.gaf coloured by team.
                            std::string archiveName = it->second->archiveName();
                            std::transform(archiveName.begin(), archiveName.end(), archiveName.begin(), [](unsigned char c) { return std::tolower(c); });
                            textures->setCurrentTextureIsLogo(archiveName.find("logos.gaf") != std::string::npos);

                            it->second->extract(*entry, *textures);
                            textures->endEntity();
                        }
                    }
                    else if (IsColorIndexName(tex))
                    {
                        // no texture by that name, but it does appear to be a color index
                        textures->addColorIndex(tex);
                    }
                }
                return textures;
            }
            catch (CompositeTexture::BufferFull&)
            {
            }
        }
    }
    return std::shared_ptr<CompositeTexture>();
}


int main(int argc, char **argv)
{
    if (argc < 3)
    {
        std::cerr << "USAGE: " << argv[0] << " <unit name> <tadata path 1> <tadata path 2> ..." << std::endl;
        std::cerr << "eg: " << argv[0] << " ARMACA_dead d:\\temp\\ccdata d:\\temp\\totala1" << std::endl;
        return 1;
    }

    const std::string unitName = argv[1];
    std::vector<rwe::_3do::Object> _3doData;

    std::vector<std::string> taDataDirs;
    for (int idxArg = 2; idxArg < argc; ++idxArg)
    {
        taDataDirs.push_back(argv[idxArg]);
    }

    for (const std::string &tadata: taDataDirs)
    {
        const std::string objects3d = tadata + "\\objects3d\\";
        std::ifstream fs(objects3d + unitName + ".3do", std::ios_base::binary);
        if (!fs.fail())
        {
            _3doData = rwe::parse3doObjects(fs, 0);
            break;
        }
    }

    if (!_3doData.empty())
    {
        std::cout << "{" << JsonKey(unitName) << "[";
        for (auto& obj : _3doData)
        {
            std::shared_ptr<CompositeTexture> textures = MakeTextures(obj, taDataDirs);
            {
                std::ostringstream fn;
                fn << unitName << "_Albedo" << textures->getWidth() << 'x' << textures->getHeight() << ".data";
                std::ofstream fs(fn.str(), std::ios_base::binary);
                textures->saveTextures(fs);
            }
            {
                std::ostringstream fn;
                fn << unitName << "_SpecTeam" << textures->getWidth() << 'x' << textures->getHeight() << ".data";
                std::ofstream fs(fn.str(), std::ios_base::binary);
                textures->saveLogos(fs);
            }

            ToJson(std::cout, obj, *textures);
            if (&obj != &_3doData.back())
            {
                std::cout << ',';
            }
        }
        std::cout << "]}";
        return 0;
    }
    return 1;
}
